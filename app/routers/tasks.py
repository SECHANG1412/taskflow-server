from email.policy import HTTP
from fastapi import APIRouter, HTTPException, status, Path
from typing import Dict, List
from ..models.task import Task, TaskCreate


# Task 관련 API들을 모아두는 라우터 객체입니다.
# main.py에서 app.include_router(...)로 이 router를 연결합니다.
# 이 파일은 Task 관련 CRUD API를 담당합니다.
# main.py는 이 router를 include_router로 가져가서 전체 FastAPI 앱에 연결합니다.
router = APIRouter()


# 서버가 실행 중일 때만 유지되는 임시 저장소입니다.
# key는 Task ID, value는 Task 객체입니다.
# tasks_db는 실제 DB 대신 사용하는 임시 저장소입니다.
# Dict[int, Task]는 "정수 ID를 key로, Task 객체를 value로 저장한다"는 타입 힌트입니다.
tasks_db: Dict[int, Task] = {}

# 새 Task를 만들 때 사용할 다음 ID 값입니다.
# 새 Task를 만들 때마다 하나씩 증가시키는 ID 값입니다.
next_task_id: int = 1


# POST /tasks/
# 클라이언트가 보낸 TaskCreate 데이터를 받아 새 Task를 생성합니다.
# summary는 Swagger 문서(/docs)에 표시될 API 설명입니다.
@router.post("/", response_mode=Task, status_code=status.HTTP_201_CREATED, summary="Create a new task")
async def create_task(task_in: TaskCreate):

    # 함수 안에서 전역 변수 next_task_id 값을 변경하기 위해 global을 사용합니다.
    # next_task_id는 함수 밖에 있는 전역 변수이므로, 값을 바꾸려면 global 선언이 필요합니다.
    global next_task_id

    # 요청 데이터(task_in)에 서버가 관리하는 id와 completed 값을 추가해 Task 객체를 만듭니다.
    # task_in.model_dump()는 Pydantic 모델을 딕셔너리로 바꿔줍니다.
    # 여기에 id를 추가해서 최종 응답용 Task 객체를 만듭니다.
    new_task = Task(id=next_task_id, **task_in.model_dump())

    # 생성한 Task를 임시 DB에 저장합니다.
    # 만들어진 Task를 tasks_db에 저장합니다.
    # 예: tasks_db[1] = 1번 Task
    tasks_db[next_task_id] = new_task

    # 다음 Task가 다른 ID를 받도록 ID 값을 1 증가시킵니다.
    next_task_id += 1

    print(f"Task created: {new_task}")
    return new_task



# GET /tasks/
# 저장된 모든 Task 목록을 반환합니다.
@router.get("/", response_model=List[Task], summary="Get all tasks")
async def read_tasks():
    print(f"Reading all tasks: {list(tasks_db.values())}")

    # 딕셔너리의 value만 꺼내 리스트 형태로 응답합니다.
    # tasks_db는 딕셔너리이므로 values()로 Task 객체들만 꺼냅니다.
    # response_model=List[Task]에 맞게 리스트로 변환해서 반환합니다.
    return list(tasks_db.values())





# GET /tasks/{task_id}
# 특정 ID를 가진 Task 하나를 조회합니다.
@router.get("/{task_id}", response_model=Task, summary="Get a specific task by ID")
async def read_task(
    # Path는 URL 경로에 들어오는 task_id 값을 검증할 때 사용합니다.
    # ge=1은 task_id가 1 이상이어야 한다는 뜻입니다.
    task_id: int = Path(..., title="조회할 Task의 ID", ge=1) 
):

    # get()은 해당 key가 없을 때 에러를 내지 않고 None을 반환합니다.
    # 그래서 없는 Task인지 안전하게 확인할 수 있습니다.
    task = tasks_db.get(task_id)

    if task is None:
        # 없는 ID로 조회하면 404 Not Found 에러를 반환합니다.
        print(f"Task not found for ID: {task_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found")
    
    print(f"Reading task: {tasks_db[task_id]}")
    return tasks_db[task_id]





# PUT /tasks/{task_id}
# 특정 ID의 Task 내용을 수정합니다.
@router.put("/{task_id}", response_model=Task, summary="Update a task")
async def update_task(
    # 수정할 title, description 데이터입니다.
    task_update: TaskCreate,
    task_id: int = Path(..., title="수정할 Task의 ID", ge=1)
):
    
    # 먼저 수정하려는 Task가 실제로 존재하는지 확인합니다.
    task = tasks_db.get(task_id)

    if task is None:
        # 수정 대상이 없으면 404 Not Found 에러를 반환합니다.
        print(f"Task not found for update: ID={task_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found")
    
    # 기존 Task 객체의 값을 요청으로 받은 값으로 교체합니다.
    # 여기서는 title과 description만 수정하고 id는 유지합니다.
    task.title = task_update.title
    task.description = task_update.description

    print(f"Task updated: {task}")

    return task





# DELETE /tasks/{task_id}
# 특정 ID의 Task를 삭제합니다.
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
async def delete_task(
    # 삭제 대상 Task의 ID입니다.
    task_id: int = Path(..., title="삭제할 Task의 ID", ge=1)
):
    # 삭제는 딕셔너리에서 해당 ID를 제거하는 방식으로 처리합니다.
    # 삭제할 Task가 없으면 404 에러를 반환합니다.
    if task_id not in tasks_db:
        print(f"Task not found for deletion: ID={task_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found")
    
    # 임시 DB에서 해당 Task를 삭제합니다.
    del tasks_db[task_id]

    print(f"Task deleted: ID={task_id}")

    # 204 응답은 본문이 없다는 의미이므로 None을 반환합니다.
    return None
