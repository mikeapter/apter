from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.auth.utils.security import (
    hash_password,
    verify_password,
    create_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class RegisterResponse(BaseModel):
    email: EmailStr
    token: str


@router.post("/register", response_model=RegisterResponse)
def register_user(payload: RegisterRequest):
    hashed = hash_password(payload.password)
    token = create_token({"sub": payload.email})

    return RegisterResponse(
        email=payload.email,
        token=token
    )
