from sqlalchemy import String, Integer, Column, null
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List, Optional, TYPE_CHECKING
from ..database import Base
from sqlalchemy import Boolean

if TYPE_CHECKING:
    from .task import Task

# User 테이블과 매핑될 User 클래스 정의
class User(Base):
    __tablename__ = "users" 

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    # --- ✨ Task 모델과의 관계 설정 (1:N 중 '1' 쪽) ✨ ---
    # 'tasks' 속성을 통해 이 User 객체에 연결된 Task 객체들의 리스트에 접근 가능
    # "Task": 연결될 상대방 모델 클래스 이름 (문자열로 지정 가능)
    # back_populates="owner": Task 모델의 'owner' 속성과 서로 연결됨을 명시 (양방향)
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="owner")

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
