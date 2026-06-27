import json
import threading
import uuid
from typing import Optional

from passlib.hash import bcrypt

from . import config

_lock = threading.Lock()


def _empty_store() -> dict:
    return {"users": []}


def _load() -> dict:
    if not config.USERS_JSON_PATH.exists():
        return _empty_store()
    with open(config.USERS_JSON_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return _empty_store()
        return json.loads(content)


def _save(data: dict) -> None:
    tmp_path = config.USERS_JSON_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp_path.replace(config.USERS_JSON_PATH)


def list_users() -> list[dict]:
    with _lock:
        return _load()["users"]


def find_by_username(username: str) -> Optional[dict]:
    for u in list_users():
        if u["username"].lower() == username.lower():
            return u
    return None


def find_by_id(user_id: str) -> Optional[dict]:
    for u in list_users():
        if u["id"] == user_id:
            return u
    return None


def create_user(username: str, password: str, email: str, group_id: str, role: str = "user") -> dict:
    with _lock:
        data = _load()
        if any(u["username"].lower() == username.lower() for u in data["users"]):
            raise ValueError(f"Username '{username}' already exists")
        user = {
            "id": uuid.uuid4().hex[:12],
            "username": username,
            "email": email,
            "passwordHash": bcrypt.hash(password),
            "groupID": group_id,
            "role": role,
        }
        data["users"].append(user)
        _save(data)
        return user


def update_user(user_id: str, **fields) -> dict:
    with _lock:
        data = _load()
        for u in data["users"]:
            if u["id"] == user_id:
                if "password" in fields and fields["password"]:
                    u["passwordHash"] = bcrypt.hash(fields.pop("password"))
                fields.pop("password", None)
                for key in ("username", "email", "groupID", "role", "theme"):
                    if key in fields and fields[key] is not None:
                        u[key] = fields[key]
                _save(data)
                return u
        raise KeyError(f"No user with id '{user_id}'")


def delete_user(user_id: str) -> None:
    with _lock:
        data = _load()
        before = len(data["users"])
        data["users"] = [u for u in data["users"] if u["id"] != user_id]
        if len(data["users"]) == before:
            raise KeyError(f"No user with id '{user_id}'")
        _save(data)


def verify_password(user: dict, password: str) -> bool:
    return bcrypt.verify(password, user["passwordHash"])


def ensure_seed_admin() -> None:
    """Create a default admin user on first run if users.json has no users."""
    with _lock:
        data = _load()
        if data["users"]:
            return
        data["users"].append(
            {
                "id": uuid.uuid4().hex[:12],
                "username": "admin",
                "email": "admin@magcollector.local",
                "passwordHash": bcrypt.hash("admin123"),
                "groupID": config.ADMIN_GROUP_ID,
                "role": "admin",
            }
        )
        _save(data)
