# Octofy Supabase setup

Run these SQL files in the Supabase Dashboard → SQL Editor, in this order:

1. `schema.sql`
2. `rls_fix.sql`
3. `direct_chat.sql`

The Android client uses the project URL and publishable key configured in `main.py`.
The publishable key is intended for client apps; never put a Supabase secret/service_role key in the APK.

For first testing, create two accounts with different email addresses and unique usernames.
If email confirmation is enabled in Supabase Auth, confirm each account using the email link before signing in.

## Current milestone

The initial Android client implements email/password signup and login, username-based direct chat creation, message sending, message history, and polling for new messages.

Push notifications and voice/video calls are not implemented in this milestone. The APK build workflow produces a debug APK for testing; a release APK needs a private signing key and secure signing configuration.
