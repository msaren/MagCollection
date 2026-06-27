import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

COLLECTIONS_DIR = REPO_ROOT / "collections"
USERS_JSON_PATH = BACKEND_DIR / "users.json"
DB_PATH = BACKEND_DIR / "magcollector.db"
THUMBNAIL_DIR = BACKEND_DIR / "thumbnails"

JWT_SECRET = os.environ.get("MAGCOLLECTOR_JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7

ADMIN_GROUP_ID = "admin"
PUBLIC_GROUP_ID = "public"

THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
