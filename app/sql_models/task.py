from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, desc, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
from ..database import Base

if TYPE_CHECKING:
    from .user import User


# Task 클래스는 데이터베이스의 task 테이블과 연결되는 SQLAlchemy ORM 모델입니다.
class Task(Base):
    # 실제 데이터베이스에서 사용할 테이블 이름입니다.
    __tablename__ = "task"

    # id는 각 Task를 구분하는 기본키입니다.
    # index=True는 id로 조회할 때 더 빠르게 찾을 수 있도록 인덱스를 만듭니다.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # title은 최대 100자의 문자열 컬럼입니다.
    # index=True라서 제목 기준 검색이 필요할 때 도움이 됩니다.
    title: Mapped[str] = mapped_column(String(100), index=True)

    # description은 선택값입니다.
    # nullable=True라서 데이터베이스에 NULL로 저장될 수 있습니다.
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # completed는 완료 여부를 저장하는 Boolean 컬럼입니다.
    # default는 파이썬 코드에서 객체를 만들 때 기본값이고, server_default는 DB 서버 쪽 기본값입니다.
    completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')


    # --- ✨ ForeignKey 및 Relationship 추가 ✨ ---
    # owner_id 컬럼: users 테이블의 id 컬럼을 참조하는 외래 키
    # ForeignKey("users.id") : '테이블이름.컬럼이름' 형식으로 지정
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)


    # User 모델과의 관계 설정 (N:1 중 'N' 쪽)
    # 'owner' 속성을 통해 이 Task 객체에 연결된 User 객체에 접근 가능
    # back_populates="tasks": User 모델의 'tasks' 속성과 서로 연결됨
    owner: Mapped["User"] = relationship("User", back_populates="tasks")



    def __repr__(self):
        # 디버깅할 때 Task 객체가 어떤 값인지 보기 쉽게 문자열로 표현합니다.
        return f"<Task(id={self.id}, title='{self.title}', completed={self.completed})>"
