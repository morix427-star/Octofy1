import os
import threading
import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window

SUPABASE_URL = "https://yazpmmblkaqfqkvvunxx.supabase.co"
SUPABASE_KEY = "sb_publishable_mY06Ec-IvvHyk7DFYhwPpQ_xYmQIyPn"

Window.clearcolor = (0.025, 0.025, 0.03, 1)

class OctofyApp(App):
    def build(self):
        self.title = "Octofy"
        self.token = None
        self.user = None
        self.current_chat = None
        self.last_message_ids = set()
        self.root_box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        self.show_auth()
        return self.root_box

    def api(self, method, path, data=None, params=None):
        headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        else:
            headers["Authorization"] = "Bearer " + SUPABASE_KEY
        response = requests.request(method, SUPABASE_URL + path, headers=headers,
                                    json=data, params=params, timeout=20)
        if response.status_code >= 400:
            try: detail = response.json().get("msg") or response.json().get("message") or response.text
            except Exception: detail = response.text
            raise Exception(str(detail)[:300])
        if response.text:
            try: return response.json()
            except Exception: return response.text
        return None

    def clear(self):
        self.root_box.clear_widgets()

    def label(self, text, size=16, color=(1,1,1,1), bold=False):
        return Label(text=text, font_size=sp(size), color=color, bold=bold,
                     halign="left", valign="middle", size_hint_y=None, height=dp(34))

    def field(self, hint, password=False):
        return TextInput(hint_text=hint, password=password, multiline=False,
                         size_hint_y=None, height=dp(48), font_size=sp(16),
                         background_color=(.13,.13,.15,1), foreground_color=(1,1,1,1),
                         hint_text_color=(.6,.6,.6,1), padding=dp(12))

    def btn(self, text, callback):
        b = Button(text=text, size_hint_y=None, height=dp(48), background_normal="",
                   background_color=(1,.12,.32,1))
        b.bind(on_release=callback)
        return b

    def show_auth(self, error=""):
        self.clear()
        self.root_box.add_widget(self.label("OCTOFY", 28, bold=True))
        self.root_box.add_widget(self.label("Вход или создание аккаунта", 16, (.7,.7,.72,1)))
        self.email = self.field("Email")
        self.password = self.field("Пароль", True)
        self.username = self.field("Имя пользователя (для регистрации)")
        self.display_name = self.field("Отображаемое имя")
        for w in (self.email, self.password, self.username, self.display_name):
            self.root_box.add_widget(w)
        if error: self.root_box.add_widget(self.label(error, 13, (1,.4,.4,1)))
        self.root_box.add_widget(self.btn("Войти", lambda *_: self.run_auth(False)))
        self.root_box.add_widget(self.btn("Создать аккаунт", lambda *_: self.run_auth(True)))
        self.root_box.add_widget(self.label("Для регистрации используй email и пароль.", 12, (.6,.6,.6,1)))

    def run_auth(self, signup):
        email, password = self.email.text.strip(), self.password.text
        username = self.username.text.strip().lstrip("@")
        display = self.display_name.text.strip() or username
        if not email or not password or (signup and len(username) < 3):
            self.show_auth("Укажи email, пароль и имя пользователя (минимум 3 символа).")
            return
        self.clear(); self.root_box.add_widget(self.label("Подключаемся к Octofy…", 18))
        threading.Thread(target=self._auth_worker, args=(signup,email,password,username,display), daemon=True).start()

    def _auth_worker(self, signup, email, password, username, display):
        try:
            if signup:
                result = self.api("POST", "/auth/v1/signup",
                    {"email":email,"password":password,
                     "data":{"username":username,"display_name":display}})
            else:
                result = self.api("POST", "/auth/v1/token?grant_type=password",
                                  {"email":email,"password":password})
            access = result.get("access_token") if isinstance(result,dict) else None
            if not access:
                raise Exception("Аккаунт создан. Проверь почту и подтверди email, затем войди.")
            self.token = access
            self.user = result.get("user", {})
            Clock.schedule_once(lambda dt: self.show_home(), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): self.show_auth(err), 0)

    def show_home(self):
        self.current_chat = None
        self.clear()
        top = BoxLayout(size_hint_y=None, height=dp(48))
        top.add_widget(self.label("OCTOFY · Чаты", 22, bold=True))
        top.add_widget(self.btn("Выйти", lambda *_: self.logout()))
        self.root_box.add_widget(top)
        self.root_box.add_widget(self.btn("＋ Новый чат по @username", lambda *_: self.new_chat_popup()))
        self.chat_list = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.chat_list.bind(minimum_height=self.chat_list.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.chat_list)
        self.root_box.add_widget(scroll)
        self.refresh_chats()
        Clock.schedule_interval(lambda dt: self.refresh_chats(), 8)

    def logout(self):
        self.token = None; self.user = None
        self.show_auth()

    def refresh_chats(self):
        if not self.token or self.current_chat: return
        threading.Thread(target=self._load_chats, daemon=True).start()

    def _load_chats(self):
        try:
            memberships = self.api("GET", "/rest/v1/conversation_members",
                params={"user_id":"eq."+self.user["id"],"select":"conversation_id","order":"joined_at.desc"})
            rows = []
            for m in memberships:
                cid = m["conversation_id"]
                members = self.api("GET", "/rest/v1/conversation_members",
                    params={"conversation_id":"eq."+cid,"select":"user_id"})
                other = next((x["user_id"] for x in members if x["user_id"] != self.user["id"]), None)
                if not other: continue
                prof = self.api("GET", "/rest/v1/profiles",
                    params={"id":"eq."+other,"select":"username,display_name"})
                title = (prof[0].get("display_name") or prof[0]["username"]) if prof else "Пользователь"
                msgs = self.api("GET", "/rest/v1/messages",
                    params={"conversation_id":"eq."+cid,"select":"body,created_at","order":"created_at.desc","limit":"1"})
                preview = msgs[0]["body"] if msgs else "Начните общение"
                rows.append((cid,title,preview))
            Clock.schedule_once(lambda dt: self._draw_chats(rows), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): self.toast(err), 0)

    def _draw_chats(self, rows):
        if not hasattr(self,"chat_list") or self.current_chat: return
        self.chat_list.clear_widgets()
        if not rows: self.chat_list.add_widget(self.label("Пока нет чатов. Нажми «Новый чат».", 15, (.7,.7,.7,1)))
        for cid,title,preview in rows:
            b = Button(text=title+"\n"+preview, halign="left", size_hint_y=None, height=dp(70),
                       background_normal="", background_color=(.12,.12,.14,1))
            b.bind(on_release=lambda inst,c=cid,t=title: self.open_chat(c,t))
            self.chat_list.add_widget(b)

    def new_chat_popup(self):
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        field = self.field("@username")
        content.add_widget(field)
        pop = Popup(title="Новый чат", content=content, size_hint=(.88,.32))
        def go(*_):
            username=field.text.strip().lstrip("@")
            pop.dismiss()
            threading.Thread(target=self._create_chat,args=(username,),daemon=True).start()
        content.add_widget(self.btn("Найти и открыть чат", go))
        pop.open()

    def _create_chat(self, username):
        try:
            result = self.api("POST","/rest/v1/rpc/create_direct_conversation",{"target_username":username})
            cid = result if isinstance(result,str) else result
            Clock.schedule_once(lambda dt: self.open_chat(str(cid), "@"+username),0)
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): self.toast(err),0)

    def open_chat(self, cid, title):
        self.current_chat = cid
        self.clear()
        head=BoxLayout(size_hint_y=None,height=dp(48))
        head.add_widget(self.btn("‹ Чаты",lambda *_: self.show_home()))
        head.add_widget(self.label(title,18,bold=True))
        self.root_box.add_widget(head)
        self.chat_area=BoxLayout(orientation="vertical",spacing=dp(6),size_hint_y=None,padding=dp(4))
        self.chat_area.bind(minimum_height=self.chat_area.setter("height"))
        sc=ScrollView(); sc.add_widget(self.chat_area); self.root_box.add_widget(sc)
        row=BoxLayout(size_hint_y=None,height=dp(52),spacing=dp(6))
        self.msg_input=self.field("Сообщение…")
        row.add_widget(self.msg_input); row.add_widget(self.btn("➤",lambda *_: self.send_message()))
        self.root_box.add_widget(row)
        self.load_messages()
        Clock.schedule_interval(lambda dt: self.load_messages(),3)

    def load_messages(self):
        cid=self.current_chat
        if not cid or not self.token:return
        threading.Thread(target=self._load_messages,args=(cid,),daemon=True).start()

    def _load_messages(self,cid):
        try:
            rows=self.api("GET","/rest/v1/messages",params={
                "conversation_id":"eq."+cid,"select":"id,sender_id,body,created_at",
                "order":"created_at.asc","limit":"200"})
            Clock.schedule_once(lambda dt:self._draw_messages(rows,cid),0)
        except Exception as e:
            Clock.schedule_once(lambda dt:self.toast(str(e)),0)

    def _draw_messages(self,rows,cid):
        if self.current_chat != cid:return
        existing={x["id"] for x in rows}
        if existing == self.last_message_ids:return
        self.last_message_ids=existing
        self.chat_area.clear_widgets()
        for m in rows:
            own=m["sender_id"]==self.user["id"]
            self.chat_area.add_widget(self.label(("Вы: " if own else "")+m["body"],15,
                (1,.55,.65,1) if own else (1,1,1,1)))

    def send_message(self):
        body=self.msg_input.text.strip()
        if not body:return
        self.msg_input.text=""
        cid=self.current_chat
        threading.Thread(target=self._send_worker,args=(cid,body),daemon=True).start()

    def _send_worker(self,cid,body):
        try:
            self.api("POST","/rest/v1/messages",{"conversation_id":cid,
                "sender_id":self.user["id"],"body":body})
            self.load_messages()
        except Exception as e:
            Clock.schedule_once(lambda dt:self.toast(str(e)),0)

    def toast(self,message):
        pop=Popup(title="Octofy",content=Label(text=str(message),text_size=(dp(280),None)),
                  size_hint=(.88,.35))
        pop.open()

if __name__ == "__main__":
    OctofyApp().run()
