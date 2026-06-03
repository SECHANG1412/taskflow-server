from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base


# SQLAlchemy가 접속할 데이터베이스 주소입니다.
# sqlite+aiosqlite는 SQLite를 비동기 방식으로 사용하겠다는 뜻입니다.
# ./sql_app.db는 프로젝트 루트에 sql_app.db 파일을 만들어 사용한다는 의미입니다.
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"


# --- ✨ 모든 ORM 모델이 상속받을 Base 클래스 정의 ✨ ---
# 모든 SQLAlchemy ORM 모델이 상속받을 공통 부모 클래스입니다.
# Base를 상속받은 클래스는 SQLAlchemy가 DB 테이블 모델로 인식합니다.
Base = declarative_base()
