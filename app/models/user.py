from pydantic import BaseModel
from typing import Optional

class UserProfile(BaseModel):
    user_id: str = "default"   # single user app
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[float] = None
    state: Optional[str] = None
    category: Optional[str] = None