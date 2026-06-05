from pydantic import BaseModel
from typing import Optional


# 로그인 성공 시 응답 본문 스키마
class Token(BaseModel):
    access_token: str
    token_type: str


# JWT 페이로드 내부의 데이터 스키마
class TokenData(BaseModel):
    email: Optional[str] = None