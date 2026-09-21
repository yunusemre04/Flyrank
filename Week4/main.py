import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from supabase import Client, create_client

load_dotenv()

app = FastAPI(
    title="FlyRank Secure Auth API",
    version="1.0.0",
    description="Secure Supabase-powered auth API for user signup, login, logout, and protected routes.",
)

security = HTTPBearer(auto_error=False)


class AuthRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_is_required(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("Email is required")
        return value.strip()

    @field_validator("password")
    @classmethod
    def password_is_required(cls, value: str) -> str:
        if value is None or not value.strip():
            raise ValueError("Password is required")
        return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid request payload"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        content = detail
    elif isinstance(detail, str):
        content = {"error": detail}
    else:
        content = {"error": "Request failed"}
    return JSONResponse(status_code=exc.status_code, content=content)


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

    return create_client(supabase_url, supabase_key)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Access token required"},
        )

    token = credentials.credentials

    try:
        client = get_supabase_client()
        user_response = client.auth.get_user(token)
        user = getattr(user_response, "user", None)

        if user is None and isinstance(user_response, dict):
            user = user_response.get("user")

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid or expired token"},
            )

        return user
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired token"},
        ) from exc


@app.get("/public/info")
async def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: AuthRequest):
    try:
        client = get_supabase_client()
        response = client.auth.sign_up({
            "email": str(payload.email),
            "password": payload.password,
        })
        return response
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": str(exc)}) from exc


@app.post("/auth/login")
async def login(payload: AuthRequest):
    try:
        client = get_supabase_client()
        response = client.auth.sign_in_with_password({
            "email": str(payload.email),
            "password": payload.password,
        })

        session = getattr(response, "session", None)
        if session is None and isinstance(response, dict):
            session = response.get("session")

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid login credentials"},
            )

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user": getattr(response, "user", None),
        }
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid login credentials"},
        ) from exc


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user=Depends(get_current_user)):
    try:
        client = get_supabase_client()
        client.auth.sign_out()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


@app.get("/protected/profile")
async def protected_profile(current_user=Depends(get_current_user)):
    return {
        "id": getattr(current_user, "id", None),
        "email": getattr(current_user, "email", None),
        "created_at": getattr(current_user, "created_at", None),
    }


@app.get("/protected/dashboard")
async def protected_dashboard(current_user=Depends(get_current_user)):
    return {
        "message": f"Welcome {getattr(current_user, 'email', 'user')}! This dashboard is protected.",
        "user_id": getattr(current_user, "id", None),
    }


@app.get("/")
async def root():
    return {"message": "FlyRank Secure API is running."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
