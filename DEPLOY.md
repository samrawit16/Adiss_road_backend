# Deploy the backend for free: Render + Neon + Brevo

Free tier facts below were checked in October 2026. Free plans change, so confirm on each site.
No credit card is needed for any of the three.

| Part | Service | Free plan |
|---|---|---|
| API (Docker) | **Render** web service | 512 MB RAM, 0.1 CPU, 750 h/month, **sleeps after 15 min idle (about 1 min to wake)**, disk is erased on sleep/redeploy |
| Database | **Neon** PostgreSQL | permanent, ~0.5 GB, suspends after 5 min idle (a few seconds to wake) |
| Email | **Brevo** HTTPS API | 300 emails/day. Render's free tier **blocks SMTP**, so Gmail SMTP cannot work there |

This project is already prepared for it:
- photos are stored **inside the database** (`STORAGE_BACKEND=db`), shrunk to 1600 px, so they survive sleeps;
- email is sent over **HTTPS** (Brevo), not SMTP;
- the model loads on first use, so the API idles at about 200 MB (about 390 MB after the first severity request);
- `APP_ENV=production` makes the server **refuse to start** with default secrets.

## 1. Put the code on GitHub
```bash
cd Adiss_road_backend
git init
git add .
git status          # the file .env must NOT be listed (it contains secrets)
git commit -m "AAGuardian backend"
git branch -M main
git remote add origin https://github.com/YOUR-USER/adiss-road-backend.git
git push -u origin main
```
Create the empty repository on github.com first (Private is fine). The model file is 78 MB, under GitHub's 100 MB limit.

## 2. Create the database (Neon)
1. neon.com > sign up > **Create project**. Region: **Europe (Frankfurt)**, closest to East Africa.
2. Click **Connect** and copy the connection string. It looks like
   `postgresql://user:password@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`.
   Keep it: this is `DATABASE_URL`.

## 3. Create the email sender (Brevo)
1. brevo.com > sign up (free).
2. **Senders, Domains & Dedicated IPs > Senders > Add a sender**: use your own email and confirm the 6-digit code.
3. **SMTP & API > API Keys > Generate a new API key**. Copy it: this is `BREVO_API_KEY`.
4. Tip: emails sent "from" a gmail.com address may be delayed or go to spam. Tell users to check spam. A custom domain fixes it.

## 4. Make two secrets
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"    # JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(16))"    # DEFAULT_ADMIN_PASSWORD (or choose your own)
```

## 5. Create the API on Render
1. render.com > sign up with GitHub > **New + > Web Service** > pick your repository.
2. Settings: **Language: Docker**, **Region: Frankfurt**, **Instance Type: Free**.
3. **Advanced > Health Check Path:** `/health`
4. **Environment Variables** (Add each one):

| Key | Value |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | the Neon string from step 2 |
| `JWT_SECRET_KEY` | secret from step 4 |
| `DEFAULT_ADMIN_EMAIL` | your admin email |
| `DEFAULT_ADMIN_PASSWORD` | strong password from step 4 |
| `STORAGE_BACKEND` | `db` |
| `BREVO_API_KEY` | key from step 3 |
| `EMAIL_FROM` | the sender you verified in Brevo |
| `OTP_CONSOLE_FALLBACK` | `false` |
| `SEED_DEMO_DATA` | `false` |

5. **Create Web Service.** The first build takes about 5 to 10 minutes (it installs scikit-learn and pandas).

## 6. Check that it works
- Open `https://YOUR-NAME.onrender.com/health` -> `{"status":"ok"}`
- Open `https://YOUR-NAME.onrender.com/docs` -> the API page.
- In the Render **Logs** you should see "Application startup complete". If you see "Refusing to start in production with unsafe settings", the message lists exactly which variable to fix.
- In `/docs` try `POST /api/v1/auth/login` with your admin email and password.

## 7. Point your apps at it
- **Flutter app:** build with your URL:
  `flutter run --dart-define=API_URL=https://YOUR-NAME.onrender.com/api/v1`
  (for an APK: `flutter build apk --dart-define=API_URL=https://YOUR-NAME.onrender.com/api/v1`).
- **Police dashboard:** deploy it free on Vercel and set the environment variable
  `BACKEND_URL=https://YOUR-NAME.onrender.com` before building.

## 8. Stop the 1-minute wake-up (optional)
uptimerobot.com (free) > **Add monitor > HTTP(s)** > URL `https://YOUR-NAME.onrender.com/health`, every 5 minutes.
One always-awake service uses about 720 of your 750 free hours.

## 9. Update later
`git add . && git commit -m "change" && git push` and Render redeploys by itself.

## Troubleshooting
| Symptom | Cause and fix |
|---|---|
| Build fails | Open the Render log. Make sure `requirements.txt` was pushed. |
| "Refusing to start in production" | A variable still has the default value. Fix the one named in the message. |
| Server restarts / "out of memory" | Free plan has 512 MB. Avoid extra services in the same instance. |
| First request is very slow | Normal after 15 min idle (Render wakes, Neon wakes). Use step 8. |
| No emails arrive | Check Render logs for "EMAIL NOT SENT". Usually the sender is not verified in Brevo or the API key is wrong. Check spam. |
| Photos missing | Make sure `STORAGE_BACKEND=db` is set. Photos taken before you set it were on the erased disk. |
| Database full | Neon free is about 0.5 GB. Check usage in the Neon dashboard. |

## Run the same image locally
`docker compose up --build` starts the API on http://localhost:8000 with PostgreSQL.
