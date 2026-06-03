from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

'''
  비유를 하나로 정리하면:

  DATABASE_URL = 주방 주소
  engine = 주방으로 연결된 출입문(DB 연결 준비물)
  sessionmaker = 직원을 뽑는 기계(세션 만드는 공장)
  Session = 실제 주문을 처리하는 직원(실제 DB 작업자)

  손님이 주문합니다.

  할 일 하나 저장해주세요

  그러면 흐름은:

  FastAPI 요청
  ↓
  sessionmaker가 Session을 하나 만듦
  ↓
  Session이 engine을 통해 DB에 연결
  ↓
  Session이 DB 작업 수행
  ↓
  작업 끝나면 Session 닫음

  입니다.
'''

# SQLAlchemy가 접속할 데이터베이스 주소입니다.
# DB 파일 위치입니다. 여기서는 sql_app.db라는 SQLite 파일을 사용합니다.
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"


# --- SQLAlchemy 비동기 엔진 생성 ---
# engine은 DB에 연결하기 위한 기본 통로입니다.
# create_async_engine 함수를 사용하여 비동기 엔진 인스턴스를 만듭니다.
engine = create_async_engine(
    DATABASE_URL,
    echo=True,      # echo=True : 실행되는 SQL 쿼리를 콘솔에 출력 (디버깅 시 유용)
    future=True     # SQLAlchemy 2.0 방식 사용 명시 (권장)
)


# --- 비동기 세션 생성기 (Session Factory) ---
# AsyncSessionLocal은 DB 작업용 session을 만들어주는 공장입니다.
AsyncSessionLocal = sessionmaker(
    bind=engine,               # 위에서 만든 engine을 사용해서 DB에 연결합니다.
    class_=AsyncSession,       # 비동기 DB 작업을 위한 세션을 만들게 합니다.
    expire_on_commit=False,    # commit 후에도 객체 값을 계속 읽을 수 있게 합니다.
    autocommit=False,          # 자동 commit을 끕니다. 직접 commit해야 DB에 반영됩니다. 
    autoflush=False            # 자동 flush를 끕니다. 직접 commit/flush할 때 DB에 보냅니다.
)


# --- SQLAlchemy 모델들이 상속받는 부모 클래스  ---
# ORM 모델들이 상속받는 부모입니다. Task 같은 테이블 모델이 Base를 상속합니다.
Base = declarative_base()


# --- 의존성 주입을 위한 DB 세션 제공 함수 ---
# 각 API 요청마다 데이터베이스 세션을 생성하고, 요청 처리가 끝나면 세션을 닫아주는 역할을 합니다.
async def get_db() -> AsyncGenerator[AsyncSession, None]:

    # 실제 DB 작업에 사용할 session을 하나 만듭니다.
    session: AsyncSession = AsyncSessionLocal()

    try:
        # yield 키워드를 사용하여 생성된 세션을 경로 작동 함수에 주입
        # 경로 작동 함수의 실행이 끝나면 다시 이 지점으로 돌아옵니다.
        yield session

    except Exception as e:
        # 에러가 나면 아직 확정되지 않은 DB 변경을 취소합니다.
        print(f"Session rollback triggered due to exception: {e}")
        await session.rollback()
        raise

    finally:
        # 요청 처리가 성공하든 실패하든 항상 세션을 닫음
        # 이는 데이터베이스 연결을 반환(release)하는 중요한 과정입니다.
        print("Closing session")
        await session.close()
