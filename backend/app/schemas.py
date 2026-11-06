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


class ReplySettingIn(BaseModel):
    # 既定はオフ（返信を受け付けない）
    allow_replies: bool = False


class IconPixelIn(BaseModel):
    # 32×32 = 1024 文字の 16 進文字列（空で未設定に戻す）
    pixel_data: str = ""
