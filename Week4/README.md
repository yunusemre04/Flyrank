# FlyRank Week 4: Secure FastAPI Auth API

This project implements the secure authentication flow described in the project plan using Python and FastAPI with Supabase Auth.

## Features

- Public route: `GET /public/info`
- User signup: `POST /auth/signup`
- User login: `POST /auth/login`
- Protected profile: `GET /protected/profile`
- Protected dashboard: `GET /protected/dashboard`
- Logout: `POST /auth/logout`
- Swagger UI documentation at `/docs`
- Bearer-token-based authentication via FastAPI security dependency

## Local setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local environment file:

```bash
copy .env.example .env
```

Then update `.env` with your real Supabase project values:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-key
PORT=8000
```

4. Run the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API endpoints

| Method | Route | Auth required | Description |
| --- | --- | --- | --- |
| GET | `/public/info` | No | Returns public information |
| POST | `/auth/signup` | No | Creates a Supabase user |
| POST | `/auth/login` | No | Signs in and returns JWT access token |
| POST | `/auth/logout` | Yes | Logs the user out |
| GET | `/protected/profile` | Yes | Returns protected user metadata |
| GET | `/protected/dashboard` | Yes | Example protected dashboard route |

## Swagger UI

Once the app is running, open:

```text
http://localhost:8000/docs
```

Use the lock icon in the Swagger UI to authorize with a Bearer token from a successful login.

## Notes

- Keep `.env` out of GitHub by ensuring `.gitignore` includes it.
- Do not commit Supabase secrets.
- Use the Supabase dashboard to generate your URL and anon key.
- If a token is missing, malformed, invalid, or expired, the API returns `401`.
