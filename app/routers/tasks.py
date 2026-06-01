from fastapi import APIRouter, HTTPException, status, Path
from typing import List
from ..models.task import Task, TaskCreate


# Task 관련 API들을 모아두는 라우터 객체입니다.
# main.py에서 app.include_router(...)로 이 router를 연결합니다.
router = APIRouter()


# 서버가 실행 중일 때만 유지되는 임시 저장소입니다.
# key는 Task ID, value는 Task 객체입니다.
tasks_db = {}

# 새 Task를 만들 때 사용할 다음 ID 값입니다.
next_task_id = 1


# POST /tasks/
# 클라이언트가 보낸 TaskCreate 데이터를 받아 새 Task를 생성합니다.
@router.post("/", response_mode=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: TaskCreate):

    # 함수 안에서 전역 변수 next_task_id 값을 변경하기 위해 global을 사용합니다.
    global next_task_id

    # 요청 데이터(task_in)에 서버가 관리하는 id와 completed 값을 추가해 Task 객체를 만듭니다.
    new_task = Task(id=next_task_id, **task_in.model_dump(), completed=False)

    # 생성한 Task를 임시 DB에 저장합니다.
    tasks_db[next_task_id] = new_task

    # 다음 Task가 다른 ID를 받도록 ID 값을 1 증가시킵니다.
    next_task_id += 1

    print(f"Task created: {new_task}")
    return new_task



# GET /tasks/
# 저장된 모든 Task 목록을 반환합니다.
@router.get("/", response_model=List[Task])
async def read_tasks():
    print(f"Reading all tasks: {list(tasks_db.values())}")

    # 딕셔너리의 value만 꺼내 리스트 형태로 응답합니다.
    return list(tasks_db.values())




# GET /tasks/{task_id}
# 특정 ID를 가진 Task 하나를 조회합니다.
@router.get("/{task_id}", response_model=Task)
async def read_task(
    # Path는 URL 경로에 들어오는 task_id 값을 검증할 때 사용합니다.
    # ge=1은 task_id가 1 이상이어야 한다는 뜻입니다.
    task_id: int = Path(..., title="조회할 Task의 ID", ge=1) 
):

    # 요청한 ID가 없으면 404 에러를 반환합니다.
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    print(f"Reading task: {tasks_db[task_id]}")
    return tasks_db[task_id]




# PUT /tasks/{task_id}
# 특정 ID의 Task 내용을 수정합니다.
@router.put("/{task_id}", response_model=Task)
async def update_task(
    # 수정할 title, description 데이터입니다.
    task_update: TaskCreate,
    task_id: int = Path(..., title="수정할 Task의 ID", ge=1)
):
    # 수정할 Task가 없으면 404 에러를 반환합니다.
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    # 기존 Task 객체를 꺼내 요청으로 받은 값으로 필드를 갱신합니다.
    existing_task = tasks_db[task_id]
    existing_task.title = task_update.title
    existing_task.description = task_update.description

    print(f"Task updated: {existing_task}")

    return existing_task



# DELETE /tasks/{task_id}
# 특정 ID의 Task를 삭제합니다.
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    # 삭제 대상 Task의 ID입니다.
    task_id: int = Path(..., title="삭제할 Task의 ID", ge=1)
):
    # 삭제할 Task가 없으면 404 에러를 반환합니다.
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    # 임시 DB에서 해당 Task를 삭제합니다.
    del tasks_db[task_id]

    print(f"Task deleted: ID={task_id}")
    
    # 204 응답은 본문이 없다는 의미이므로 None을 반환합니다.
    return None
