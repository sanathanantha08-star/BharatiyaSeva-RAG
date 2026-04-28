from fastapi import APIRouter
from app.models.user import UserProfile
from app.db.mongodb.client import get_db

router = APIRouter()
COLLECTION = "users"

@router.post("/")
async def save_user(profile: UserProfile):
    db = get_db()
    await db[COLLECTION].replace_one(
        {"user_id": profile.user_id},
        profile.model_dump(),
        upsert=True,
    )
    return {"message": "Saved"}

@router.get("/")
async def get_user():
    db = get_db()
    user = await db[COLLECTION].find_one({"user_id": "default"})
    if not user:
        return {}
    user.pop("_id", None)
    return user