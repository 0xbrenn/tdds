# IOPn-Early-Badge
The Early Badge Platform For IOPn

This project implements an early-access badge system with Telegram bot integration, Discord and Twitter OAuth, email fallback registration, and Supabase-powered backend tracking.

---

##  Project Status Checklist

| Feature / Task                                      | Status     |
|-----------------------------------------------------|------------|
| Supabase `badge_users` table                        | Done       |
| Telegram authentication (`/auth/telegram`)          | Done       |
| Discord OAuth login (`/auth/discord/callback`)      | Done       |
| Twitter OAuth login (`/auth/twitter/login`)         | Done       |
| `.env` file usage for secrets                       | Done       |
| FastAPI router structure                            | Done       |
| Telegram bot `/start` and `/check`                  | Done       |
| `/badge/status/{telegram_id}` endpoint              | Done       |
| `/badge/issue` endpoint                             | Done       |
| Username-based fallback linking                     | Done       |
| Manual account linking via `/auth/telegram/link-account` | Done   |
| Delete-then-update logic for duplicate Twitter ID   | Done       |
| API key protection for sensitive endpoints          | Not done   |
| Email fallback authentication                       | Done       |
| `/badge/status/{twitter_id}` support                | Done       |
| Frontend login buttons (Twitter, Discord)           | Not done   |
| Telegram `/verify` to confirm cross-login identity  | Done       |
| Cookie/legal consent popup                          | Not done   |

---
## Supabase Table: badge_users

| Column            | Type    | Notes                                    |
|-------------------|---------|------------------------------------------|
| id                | int     | Primary Key                              |
| telegram_id       | text    | Nullable, unique                         |
| discord_id        | text    | Nullable, unique                         |
| twitter_id        | text    | Nullable, unique                         |
| username          | text    | Shared identifier                        |
| first_name        | text    | Optional                                 |
| last_name         | text    | Optional                                 |
| email             | text    | Optional, unique                         |
| badge_issued      | boolean | Default: false                           |
| telegram_joined   | boolean | True if user joined Telegram             |
| discord_joined    | boolean | True if user logged in via Discord       |
| twitter_followed  | boolean | True if user followed via Twitter OAuth  |
| email_added       | boolean | True if user registered with email       |

##  Features

- Telegram authentication and badge status checking via bot
- Discord and Twitter OAuth2 login with auto-linking
- Email fallback authentication
- Supabase backend with full user progress tracking
- REST API endpoints for badge issue, status, and account linking
- Telegram bot `/start` and `/check` support
- Track `telegram_joined`, `discord_joined`, `twitter_followed`, and `email_added` in Supabase

---

##  API Endpoints

### Telegram
- `POST /auth/telegram` – Store Telegram user
- `GET /auth/telegram/badge/status/{telegram_id}` – Check badge status
- `POST /auth/telegram/badge/issue` – Issue a badge
- `GET /auth/telegram/verify/{telegram_id}` – Confirm identity
- `POST /auth/telegram/link-account` – Link Twitter ID

### Discord
- `GET /auth/discord/callback` – Handle Discord OAuth2
- `GET /status/{discord_id}` – Check badge status

### Twitter
- `GET /auth/twitter/login` – OAuth entry point
- `GET /auth/twitter/callback` – Handle login and linking
- `GET /auth/twitter/status/{twitter_id}` – Badge status by Twitter ID

### Email
- `POST /auth/email/register` – Store fallback email
- `GET /auth/email/status/{email}` – Check badge status

---

## Running Locally

### Environment Variables (.env)
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret
TWITTER_REDIRECT_URI=http://localhost:8000/auth/twitter/callback
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key


### Start FastAPI backend
uvicorn backend.main:app --reload

Tekegram bot 
python backend/bot_check.py


