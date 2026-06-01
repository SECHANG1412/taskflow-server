from fastapi import FastAPI
from .routers import tasks

# FastAPI 애플리케이션 객체를 생성합니다.
# 이 app 객체가 프로젝트의 중심이 되고, 라우터와 엔드포인트가 여기에 연결됩니다.
app = FastAPI(title="ToDo List API - 실전 프로젝트")


# tasks.py에 정의된 Task 관련 라우터를 메인 앱에 연결합니다.
app.include_router(
    tasks.router,       # app/routers/tasks.py 안에 있는 router 객체입니다.
    prefix="/tasks",    # 이 라우터의 모든 API 앞에 /tasks 경로를 붙입니다.
    tags=["Task"]       # Swagger 문서(/docs)에서 이 API들을 Task 그룹으로 보여줍니다.
)


# GET /
# 서버가 정상적으로 실행 중인지 간단히 확인할 수 있는 기본 엔드포인트입니다.
@app.get("/")
async def root():
    return {"message": "Welcome to the ToDo List API!"}
