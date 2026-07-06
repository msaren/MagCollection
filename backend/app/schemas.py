# Request bodies for the FastAPI endpoints in main.py. Update-style models use
# Optional fields defaulting to None so callers can send only the fields they're changing.
from typing import Literal, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    email: str
    groupID: str
    role: str = "user"


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    groupID: Optional[str] = None
    role: Optional[str] = None


class MagazineUpdateRequest(BaseModel):
    title: Optional[str] = None
    groupID: Optional[str] = None
    userID: Optional[str] = None


class CollectionUpdateRequest(BaseModel):
    groupID: Optional[str] = None
    icon: Optional[str] = None


class ThemeUpdateRequest(BaseModel):
    theme: Literal["light", "dark"]
