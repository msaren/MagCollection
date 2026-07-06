from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import auth, config, db, scanner, thumbnails, users_store
from .schemas import (
    CollectionUpdateRequest,
    LoginRequest,
    MagazineUpdateRequest,
    ThemeUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)

app = FastAPI(title="MagCollector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.init_db()
    users_store.ensure_seed_admin()
    scanner.scan()


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "groupID": user["groupID"],
        "role": user["role"],
        "theme": user.get("theme", "light"),
    }


MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".epub": "application/epub+zip",
}


def public_magazine(row) -> dict:
    return {
        "id": row["id"],
        "collection": row["collection"],
        "filename": row["filename"],
        "dirpath": row["dirpath"],
        "title": row["title"],
        "groupID": row["groupID"],
        "userID": row["userID"],
        "size": row["size"],
        "mtime": row["mtime"],
        "filetype": Path(row["filename"]).suffix.lower().lstrip("."),
    }


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
def login(body: LoginRequest):
    user = users_store.find_by_username(body.username)
    if user is None or not users_store.verify_password(user, body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = auth.create_token(user)
    return {"token": token, "user": public_user(user)}


@app.get("/api/me")
def me(user: dict = Depends(auth.get_current_user)):
    return public_user(user)


@app.put("/api/me/theme")
def update_my_theme(body: ThemeUpdateRequest, user: dict = Depends(auth.get_current_user)):
    updated = users_store.update_user(user["id"], theme=body.theme)
    return public_user(updated)


# ---------------------------------------------------------------------------
# Collections & magazines (regular user access)
# ---------------------------------------------------------------------------

@app.get("/api/collections")
def list_collections(user: dict = Depends(auth.get_current_user)):
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM collections ORDER BY name").fetchall()
    result = []
    for row in rows:
        if not auth.can_access(user, row["groupID"], None):
            continue
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM magazines WHERE collection = ?", (row["name"],)
        ).fetchone()["c"]
        result.append({"name": row["name"], "groupID": row["groupID"], "icon": row["icon"], "magazineCount": count})
    return result


@app.get("/api/collections/{name}/browse")
def browse_collection(name: str, path: str = "", user: dict = Depends(auth.get_current_user)):
    """List the folders and magazines directly inside `path` within a collection.

    `path` is a `/`-separated subdirectory path relative to the collection root
    (empty string for the collection's top level), mirroring the on-disk layout
    under collections/<name>/.
    """
    conn = db.get_conn()
    collection = conn.execute("SELECT * FROM collections WHERE name = ?", (name,)).fetchone()
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not auth.can_access(user, collection["groupID"], None):
        raise HTTPException(status_code=403, detail="No access to this collection")

    path = path.strip("/")
    prefix = f"{path}/" if path else ""

    rows = conn.execute(
        "SELECT * FROM magazines WHERE collection = ? ORDER BY title", (name,)
    ).fetchall()

    magazines = []
    folder_counts: dict[str, int] = {}
    for row in rows:
        if not auth.can_access(user, row["groupID"], row["userID"]):
            continue
        dirpath = row["dirpath"] or ""
        if dirpath == path:
            magazines.append(row)
        elif dirpath.startswith(prefix):
            folder_name = dirpath[len(prefix):].split("/", 1)[0]
            folder_counts[folder_name] = folder_counts.get(folder_name, 0) + 1

    folders = [
        {"name": folder_name, "path": f"{prefix}{folder_name}", "magazineCount": count}
        for folder_name, count in sorted(folder_counts.items())
    ]

    return {
        "path": path,
        "folders": folders,
        "magazines": [public_magazine(r) for r in magazines],
    }


def _get_magazine_or_404(magazine_id: int):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM magazines WHERE id = ?", (magazine_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Magazine not found")
    return row


@app.get("/api/magazines/{magazine_id}/file")
def get_magazine_file(magazine_id: int, user: dict = Depends(auth.get_current_user)):
    row = _get_magazine_or_404(magazine_id)
    if not auth.can_access(user, row["groupID"], row["userID"]):
        raise HTTPException(status_code=403, detail="No access to this magazine")
    file_path = config.COLLECTIONS_DIR / row["relpath"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    media_type = MEDIA_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(file_path, media_type=media_type, filename=row["filename"])


@app.get("/api/magazines/{magazine_id}/thumbnail")
def get_magazine_thumbnail(magazine_id: int, user: dict = Depends(auth.get_current_user)):
    row = _get_magazine_or_404(magazine_id)
    if not auth.can_access(user, row["groupID"], row["userID"]):
        raise HTTPException(status_code=403, detail="No access to this magazine")
    try:
        path = thumbnails.ensure_thumbnail(row["relpath"])
    except Exception:
        raise HTTPException(status_code=500, detail="Could not render thumbnail")
    return FileResponse(path, media_type="image/png")


# ---------------------------------------------------------------------------
# Admin: users
# ---------------------------------------------------------------------------

@app.get("/api/admin/users")
def admin_list_users(user: dict = Depends(auth.require_admin)):
    return [public_user(u) for u in users_store.list_users()]


@app.post("/api/admin/users", status_code=201)
def admin_create_user(body: UserCreateRequest, user: dict = Depends(auth.require_admin)):
    try:
        created = users_store.create_user(
            username=body.username,
            password=body.password,
            email=body.email,
            group_id=body.groupID,
            role=body.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return public_user(created)


@app.put("/api/admin/users/{user_id}")
def admin_update_user(user_id: str, body: UserUpdateRequest, user: dict = Depends(auth.require_admin)):
    try:
        updated = users_store.update_user(user_id, **body.model_dump())
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return public_user(updated)


@app.delete("/api/admin/users/{user_id}", status_code=204)
def admin_delete_user(user_id: str, user: dict = Depends(auth.require_admin)):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    try:
        users_store.delete_user(user_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Admin: collection scanner
# ---------------------------------------------------------------------------

@app.post("/api/admin/scan")
def admin_scan(user: dict = Depends(auth.require_admin)):
    return scanner.scan()


@app.get("/api/admin/collections")
def admin_list_collections(user: dict = Depends(auth.require_admin)):
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM collections ORDER BY name").fetchall()
    result = []
    for row in rows:
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM magazines WHERE collection = ?", (row["name"],)
        ).fetchone()["c"]
        result.append({"name": row["name"], "groupID": row["groupID"], "icon": row["icon"], "magazineCount": count})
    return result


@app.put("/api/admin/collections/{name}")
def admin_update_collection(name: str, body: CollectionUpdateRequest, user: dict = Depends(auth.require_admin)):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM collections WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    updates = body.model_dump(exclude_none=True)
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with db.tx() as c:
            c.execute(f"UPDATE collections SET {set_clause} WHERE name = ?", (*updates.values(), name))
    row = conn.execute("SELECT * FROM collections WHERE name = ?", (name,)).fetchone()
    return {"name": row["name"], "groupID": row["groupID"], "icon": row["icon"]}


# ---------------------------------------------------------------------------
# Admin: magazine properties editor
# ---------------------------------------------------------------------------

@app.get("/api/admin/magazines")
def admin_list_magazines(user: dict = Depends(auth.require_admin)):
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM magazines ORDER BY collection, title").fetchall()
    return [public_magazine(r) for r in rows]


@app.put("/api/admin/magazines/{magazine_id}")
def admin_update_magazine(magazine_id: int, body: MagazineUpdateRequest, user: dict = Depends(auth.require_admin)):
    row = _get_magazine_or_404(magazine_id)
    updates = body.model_dump(exclude_none=True)
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with db.tx() as c:
            c.execute(f"UPDATE magazines SET {set_clause} WHERE id = ?", (*updates.values(), magazine_id))
    return public_magazine(_get_magazine_or_404(magazine_id))
