from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, desc
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
from ..database import Base


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

    def __repr__(self):
        # 디버깅할 때 Task 객체가 어떤 값인지 보기 쉽게 문자열로 표현합니다.
        return f"<Task(id={self.id}, title='{self.title}', completed={self.completed})>"
