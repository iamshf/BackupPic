from pydantic import BaseModel
from datetime import datetime

class BaiduTokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    expire_at: datetime
