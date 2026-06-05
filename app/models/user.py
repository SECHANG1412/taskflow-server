from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# 공통 사용자 속성
class UserBase(BaseModel):
    # 모든 User 관련 Pydantic 모델이 공통으로 가지는 이메일 필드입니다.
    # EmailStr은 이메일 형식이 맞는지 검증해줍니다.
    email: EmailStr = Field(..., examples=["john.doe@example.com"])


# 사용자 생성 시 요청 본문 모델 (비밀번호 포함)
class UserCreate(UserBase):
    # 회원가입 요청에서만 사용하는 원본 비밀번호입니다.
    # DB에는 이 값 그대로 저장하지 않고, 해싱한 값만 저장해야 합니다.
    password: str = Field(..., min_length=8, description="비밀번호는 최소 8자 이상이어야 합니다.")


# 사용자 정보 응답 모델 (비밀번호 제외)
class User(BaseModel):
    # API 응답으로 돌려줄 사용자 ID입니다.
    id: int
    # SQLAlchemy ORM 객체를 Pydantic 응답 모델로 변환할 수 있게 해주는 설정입니다.
    # 예: SQLAlchemy User 객체를 그대로 return해도 id/email을 읽어 응답으로 만들 수 있습니다.
    model_config = {"from_attributes": True}
