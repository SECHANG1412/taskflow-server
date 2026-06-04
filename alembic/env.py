import asyncio
from logging.config import fileConfig
import os
import sys

from sqlalchemy import pool

# ✨ 비동기 엔진 설정을 위해 async_engine_from_config 사용 ✨
from sqlalchemy.ext.asyncio import async_engine_from_config

# context는 Alembic 실행 상태와 설정을 다루는 핵심 객체입니다.
from alembic import context

# --- ✨ 프로젝트 루트 경로 추가 (env.py가 app 모듈을 찾도록) ✨ ---
# env.py 파일의 부모 디렉토리의 부모 디렉토리 (즉, 프로젝트 루트)를 sys.path에 추가
# Alembic은 alembic 폴더 기준으로 실행되므로 app 패키지를 못 찾을 수 있습니다.
# 프로젝트 루트를 import 경로에 추가해서 app.database 같은 모듈을 찾게 합니다.
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
# --------------------------------------------------------------


# --- ✨ Base 및 모델 임포트 ✨ ---
from app.database import Base  # database.py의 Base 임포트
import app.sql_models.task     # task 모델 모듈 임포트 (Base.metadata가 인식하도록)
import app.sql_models.user 
# 만약 다른 모델 파일들이 있다면 모두 임포트해주는 것이 안전합니다.
# -------------------------------------



# alembic.ini 설정을 코드에서 사용할 수 있게 가져옵니다.
config = context.config

if config.config_file_name is not None:
    # alembic.ini에 적힌 로그 설정을 적용합니다.
    fileConfig(config.config_file_name)




# --- ✨ target_metadata 설정 ✨ ---
# 우리의 모델 메타데이터 지정!
# autogenerate가 비교할 기준 설계도입니다.
# SQLAlchemy 모델 구조와 실제 DB 구조를 비교할 때 이 값을 사용합니다.
target_metadata = Base.metadata




def run_migrations_offline() -> None:
    # offline 모드는 DB에 직접 접속하지 않고 SQL 스크립트만 만들 때 쓰는 방식입니다.
    # 일반 개발 중에는 보통 online 모드를 더 자주 사용합니다.

    # context 설정 및 마이그레이션 실행 (run_sync 내부에서 호출될 함수)
    # Alembic에게 어떤 연결과 어떤 모델 설계도를 기준으로 실행할지 알려줍니다.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)

    with context.begin_transaction():
        # 실제 마이그레이션 실행 지점입니다.
        context.run_migrations()



def do_run_migrations(connection):
    # 비동기 연결 안에서 실제 Alembic 마이그레이션을 실행하기 위한 동기 함수입니다.
    # connection은 DB 연결이고, target_metadata는 SQLAlchemy 모델 설계도입니다.
    # context 설정 및 마이그레이션 실행 (run_sync 내부에서 호출될 함수)
    # Alembic 실행 환경에 DB 연결과 모델 메타데이터를 등록합니다.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        # versions 폴더의 마이그레이션 스크립트를 실행합니다.
        context.run_migrations()



# --- ✨ run_migrations_online 함수 비동기 방식으로 수정 ✨ ---
async def run_migrations_online() -> None:

    # alembic.ini의 sqlalchemy.url 값을 읽어서 비동기 DB 엔진을 만듭니다.
    # 이 엔진으로 실제 DB에 접속해서 마이그레이션을 적용합니다.
    # config 섹션에서 비동기 엔진 생성
    connectable =async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True
    )

    # 비동기적으로 DB 연결
    # connectable.connect()로 DB에 실제 연결합니다.
    async with connectable.connect() as connection:
        # 동기적인 마이그레이션 함수(do_run_migrations)를
        # 비동기 연결의 run_sync 메서드 내에서 실행
        # Alembic의 실제 마이그레이션 실행은 동기 함수라서 run_sync로 감싸 실행합니다.
        await connection.run_sync(do_run_migrations)

    # 엔진 연결 종료
    # 마이그레이션이 끝나면 엔진 자원을 정리합니다.
    await connectable.dispose()





if context.is_offline_mode():
    # offline 모드이면 DB 접속 없이 SQL만 생성하는 흐름으로 실행합니다.
    run_migrations_offline()
else:
    # online 모드이면 실제 DB에 접속해서 마이그레이션을 적용합니다.
    # 온라인 모드일 경우 비동기 함수 실행
    asyncio.run(run_migrations_online())
