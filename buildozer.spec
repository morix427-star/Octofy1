[app]
title = Octofy
package.name = octofy
package.domain = com.morix427
source.dir = .
source.include_exts = py,kv,png,jpg,atlas
version = 0.1.0
requirements = python3==3.12.9,hostpython3==3.12.9,kivy,requests,urllib3,certifi,idna,charset_normalizer
p4a.branch = develop
p4a.commit = d2ee8c5
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 35
android.ndk = 25b
android.minapi = 26
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
p4a.bootstrap = sdl2
[buildozer]
log_level = 2
warn_on_root = 1
