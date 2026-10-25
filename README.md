# Campusly (Django backend)

Sign-in with an emailed 6-digit code, listings with photos, buyer messages and inbox.
Everything runs on Django. No Supabase.

## Run it on your computer (about 5 minutes)

1. Install Python 3.9 or newer from python.org.
2. Open a terminal in this folder and run:

   ```
   python -m venv venv
   venv\Scripts\activate            (Windows)
   source venv/bin/activate         (Mac / Linux)
   pip install -r requirements.txt
   copy .env.example .env           (Windows)   |   cp .env.example .env   (Mac / Linux)
   python manage.py makemigrations core
   python manage.py migrate
   python manage.py runserver
   ```
3. Open http://127.0.0.1:8000 in your browser.

### Testing without email
Leave `EMAIL_HOST_USER` empty in `.env`. When you ask for a code, Django prints the whole
email (with the 6-digit code) in the terminal where `runserver` is running. Copy the code
from there. Nothing is sent to the internet.

### Sending real emails (Brevo)
Fill these in `.env`, then restart the server:

```
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=<your Brevo SMTP login, ends in @smtp-brevo.com>
EMAIL_HOST_PASSWORD=<your Brevo SMTP key>
EMAIL_FROM=<sender address verified in Brevo>
```
The sender name shown to students is "Campusly".

### Admin page (optional)
`python manage.py createsuperuser`, then open http://127.0.0.1:8000/admin/ to see users,
listings and messages.

## What is where
- `core/views.py`: sign-in codes, listings, messages (JSON API)
- `core/models.py`: EmailCode, Listing, Message
- `core/emails.py`: the "Campusly" verification email (HTML and plain text)
- `core/pages/`: the website pages (index, login, home)
- `campusly/settings.py`: settings (reads `.env`)

## Safety rules built in
- Codes: 6 digits, stored as a hash, expire in 10 minutes, 5 wrong tries allowed,
  1 request per minute and 5 per hour for each email.
- Only the owner can delete or mark sold their listing.
- A seller can reply only to people who messaged about that listing.
- Photos: JPG, PNG, GIF or WebP only, checked by file content, max 3 MB, renamed randomly.
- CSRF protection and secure cookies when `DJANGO_DEBUG=0`.

## Before going live (important)
- Set `DJANGO_DEBUG=0`, a long random `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`
  (your domain) and `DJANGO_CSRF_TRUSTED_ORIGINS` (https://your-domain).
- Use HTTPS. Use a real database (PostgreSQL) and run with gunicorn.
- Uploaded photos are served by Django only in debug mode. In production, serve `/media/`
  from your host's disk or cloud storage.
- Run `python manage.py collectstatic` if you use the admin page in production.
