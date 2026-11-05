"""floppy.io — リクエストスキーマ"""

from __future__ import annotations

from pydantic import BaseModel


class RegisterIn(BaseModel):
    username: str = ""
    password: str = ""
    display_name: str = ""


class LoginIn(BaseModel):
    username: str = ""
    password: str = ""


class IdIn(BaseModel):
    id: int = 0


class FollowIn(BaseModel):
    username: str = ""
    id: int = 0


class ProfileIn(BaseModel):
    display_name: str = ""
    bio: str = ""


class PasswordIn(BaseModel):
    current_password: str = ""
    new_password: str = ""
