# Feast Finder

Latrobe Valley Deals is a Flask app for finding local food specials by day and meal type. Users can browse deals, sort nearby offers, open locations in Google Maps, and submit new business deals for review. Includes an admin panel for managing businesses, locations, deals, and requests.

Set `ADMIN_PASSWORD` before the first run to create the initial admin password. Later password changes are stored locally in `password.txt`, which is ignored by Git. Set `SECRET_KEY` in production so Flask sessions stay secure and survive app reloads.

To protect the admin login with Google reCAPTCHA v3, set `RECAPTCHA_SITE_KEY` and `RECAPTCHA_SECRET_KEY` in the environment. Optionally set `RECAPTCHA_MIN_SCORE` to adjust the default score threshold of `0.5`.

You can also create a local `.env` file from `.env.example`. Keep `.env` out of Git because it contains secrets. On PythonAnywhere, pull the latest code, create `.env` in the project folder with `nano .env`, add the real keys, then reload the web app.

The admin login locks out a client IP for 60 seconds after 5 incorrect password attempts.
