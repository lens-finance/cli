from pydantic import BaseModel

class PlaidConnection(BaseModel):
    name: str
    access_token: str
    item_id: str