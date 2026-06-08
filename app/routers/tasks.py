import re
from fastapi import APIRouter, HTTPException, status, Path, Depends 
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.future import select 

from ..models.task import Task as PydanticTask, TaskCreate 
from ..sql_models.task import Task as SQLAlchemyTask 
from ..sql_models.user import User as SQLAlchemyUser
from ..database import get_db
from ..security import get_current_user


router = APIRouter()


# 현재 로그인한 사용자의 새 할 일을 생성합니다.
@router.post("/", response_model=PydanticTask, status_code=status.HTTP_201_CREATED, summary="Create a new task for the current user")
async def create_task(
    task_in: TaskCreate,                                      # 클라이언트가 요청 본문으로 보낸 새 할 일 데이터입니다.
    db: AsyncSession = Depends(get_db),                       # 이번 요청에서 DB 작업을 처리할 SQLAlchemy 세션입니다.
    current_user: SQLAlchemyUser = Depends(get_current_user)  # JWT 검증을 통과한 현재 로그인 사용자입니다.
):

    # task_in은 Pydantic 모델입니다.
    # SQLAlchemy 모델인 SQLAlchemyTask를 만들려면 dict 형태로 풀어 넣어야 하므로 model_dump()를 사용합니다.
    # owner_id에는 현재 로그인한 사용자의 id를 직접 넣습니다.
    # 이렇게 해야 새 할 일이 "누구의 할 일인지" DB에 저장됩니다.
    db_task = SQLAlchemyTask(**task_in.model_dump(), owner_id=current_user.id)

    
    db.add(db_task)             # add()는 바로 DB에 저장한다는 뜻이 아니라, 세션에 "이 객체를 저장할 예정"이라고 등록하는 단계입니다.
    await db.commit()           # commit()을 해야 INSERT SQL이 실제 DB에 반영됩니다.
    await db.refresh(db_task)   # refresh()는 DB에 저장된 최신 값을 다시 Python 객체에 반영합니다.

    print(f"User '{current_user.email}' created task: {db_task.title}")

    # 생성된 Task 객체를 응답으로 반환합니다.
    # response_model=PydanticTask가 있으므로 FastAPI는 이 객체를 응답용 Pydantic 형태로 변환합니다.
    return db_task



# 현재 로그인한 사용자의 할 일 목록을 조회합니다.
@router.get("/", response_model=List[PydanticTask], summary="Get tasks for the current user")
async def read_tasks(
    db: AsyncSession = Depends(get_db),                       # 이번 요청에서 DB 조회를 처리할 SQLAlchemy 세션입니다.
    current_user: SQLAlchemyUser = Depends(get_current_user), # JWT 검증을 통과한 현재 로그인 사용자입니다.
    skip: int = 0,                                            # 조회 결과 앞에서 몇 개를 건너뛸지 정합니다.
    limit: int = 100                                          # 한 번에 최대 몇 개까지 가져올지 정합니다.
):

    # select(SQLAlchemyTask)는 task 테이블에서 Task 데이터를 조회하겠다는 SELECT 쿼리입니다.
    # where(SQLAlchemyTask.owner_id == current_user.id)는 현재 로그인한 사용자의 할 일만 가져오겠다는 조건입니다.
    # offset(skip)은 앞의 skip개를 건너뜁니다.
    # limit(limit)은 최대 limit개만 가져옵니다.
    query = select(SQLAlchemyTask).where(SQLAlchemyTask.owner_id == current_user.id).offset(skip).limit(limit)

    # execute()는 위에서 만든 SELECT 쿼리를 실제 DB에 보내 실행합니다.
    # result에는 DB가 돌려준 조회 결과가 들어갑니다.
    result = await db.execute(query)

    # scalars()는 조회 결과에서 SQLAlchemyTask 객체만 꺼내는 역할을 합니다.
    # all()은 그 객체들을 전부 리스트로 만듭니다.
    tasks = result.scalars().all()

    print(f"User '{current_user.email}' reading their tasks ({len(tasks)} items)")

    # 현재 로그인한 사용자의 할 일 목록만 반환합니다.
    # 다른 사용자의 할 일은 owner_id 조건에서 걸러졌기 때문에 응답에 포함되지 않습니다.
    return tasks


# 현재 로그인한 사용자의 특정 할 일 하나를 조회합니다.
@router.get("/{task_id}", response_model=PydanticTask, summary="Get a specific task by ID for the current user")
async def read_task(
    task_id: int = Path(..., ge=1),                          # URL 경로에서 받은 task_id입니다. 1 이상만 허용합니다.
    db: AsyncSession = Depends(get_db),                      # 이번 요청에서 DB 조회를 처리할 SQLAlchemy 세션입니다.
    current_user: SQLAlchemyUser = Depends(get_current_user) # JWT 검증을 통과한 현재 로그인 사용자입니다.
):
    
    # 특정 task_id만으로 조회하면 다른 사용자의 할 일도 조회될 수 있습니다.
    # 그래서 task id 조건과 owner_id 조건을 함께 사용합니다.
    # 이 조건은 "요청한 task_id의 할 일이면서, 현재 로그인한 사용자의 할 일인 것"만 찾습니다.
    query = select(SQLAlchemyTask).where(SQLAlchemyTask.id == task_id, SQLAlchemyTask.owner_id == current_user.id)

    # 위 SELECT 쿼리를 실제 DB에 실행합니다.
    result = await db.execute(query)

    # 결과가 있으면 Task 객체 하나를 가져오고, 없으면 None을 반환합니다.
    # 여기서 None이 나오는 경우는 task_id가 없거나, 있어도 현재 사용자의 할 일이 아닌 경우입니다.
    task = result.scalar_one_or_none()

    # task가 None이면 클라이언트에게 404를 반환합니다.
    # 보안상 "다른 사용자의 할 일입니다"라고 알려주지 않고, 그냥 찾을 수 없다고 처리합니다.
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Task not found"
        )
    
    print(f"User '{current_user.email}' reading task ID: {task_id}")

    # 조회에 성공한 할 일 객체를 반환합니다.
    return task





# 현재 로그인한 사용자의 특정 할 일을 수정합니다.
@router.put("/{task_id}", response_model=PydanticTask, summary="Update a task for the current user")
async def update_task(
    task_update: TaskCreate,                                 # 클라이언트가 요청 본문으로 보낸 수정 데이터입니다.
    task_id: int = Path(..., ge=1),                          # URL 경로에서 받은 task_id입니다. 1 이상만 허용합니다.
    db: AsyncSession = Depends(get_db),                      # 이번 요청에서 DB 작업을 처리할 SQLAlchemy 세션입니다.
    current_user: SQLAlchemyUser = Depends(get_current_user) # JWT 검증을 통과한 현재 로그인 사용자입니다.
):
    

    # 수정할 대상을 먼저 DB에서 찾습니다.
    # 여기서도 task_id와 owner_id를 함께 확인합니다.
    # 이렇게 해야 현재 로그인한 사용자가 자기 할 일만 수정할 수 있습니다.
    query = select(SQLAlchemyTask).where(SQLAlchemyTask.id == task_id, SQLAlchemyTask.owner_id == current_user.id)

    # 수정 대상 조회 쿼리를 DB에 실행합니다.
    result = await db.execute(query)

    # 수정할 Task 객체를 하나 꺼냅니다.
    # 조건에 맞는 데이터가 없으면 None이 됩니다.
    db_task = result.scalar_one_or_none()

    # 수정할 대상이 없으면 404를 반환합니다.
    # 이 처리가 없으면 None에 값을 넣으려다 서버 에러가 날 수 있습니다.
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Task not found"
        )


    # Pydantic 모델인 task_update를 dict로 바꿉니다.
    # 예를 들어 {"title": "새 제목", "description": "새 설명"} 같은 형태가 됩니다.
    update_data = task_update.model_dump(exclude_unset=True)

    # update_data에 들어있는 key, value를 하나씩 꺼내 DB 객체에 반영합니다.
    # key가 "title"이면 db_task.title = value를 하는 것과 같은 효과입니다.
    # key가 "description"이면 db_task.description = value를 하는 것과 같습니다.
    for key, value in update_data.items():
        setattr(db_task, key, value)

    # 여기까지는 Python 객체의 값만 바뀐 상태입니다.
    # commit()을 해야 UPDATE SQL이 실제 DB에 반영됩니다.
    await db.commit()

    # DB에 저장된 최신 상태를 다시 db_task 객체에 반영합니다.
    # 수정 후 응답을 정확하게 돌려주기 위해 사용합니다.
    await db.refresh(db_task)

    print(f"User '{current_user.email}' updated task ID: {task_id}")

    # 수정이 끝난 할 일 객체를 반환합니다.
    return db_task


# 현재 로그인한 사용자의 특정 할 일을 삭제합니다.
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task for the current user")
async def delete_task(
    task_id: int = Path(..., ge=1),                          # URL 경로에서 받은 task_id입니다. 1 이상만 허용합니다.
    db: AsyncSession = Depends(get_db),                      # 이번 요청에서 DB 작업을 처리할 SQLAlchemy 세션입니다.
    current_user: SQLAlchemyUser = Depends(get_current_user) # JWT 검증을 통과한 현재 로그인 사용자입니다.
):
    
    # 삭제할 대상을 먼저 DB에서 찾습니다.
    # 삭제도 task_id만 보면 안 되고, owner_id까지 함께 확인해야 합니다.
    # 그래야 현재 로그인한 사용자가 자기 할 일만 삭제할 수 있습니다.
    query = select(SQLAlchemyTask).where(SQLAlchemyTask.id == task_id, SQLAlchemyTask.owner_id == current_user.id)

    # 삭제 대상 조회 쿼리를 DB에 실행합니다.
    result = await db.execute(query)

    # 삭제할 Task 객체를 하나 꺼냅니다.
    # 조건에 맞는 데이터가 없으면 None이 됩니다.
    db_task = result.scalar_one_or_none()

    # 삭제할 대상이 없으면 404를 반환합니다.
    # 실제로 id가 없거나, 다른 사용자의 할 일이라서 조건에 걸리지 않은 경우입니다.
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Task not found"
        )
    

    # delete()는 바로 DB에서 지우는 것이 아니라, 세션에 "이 객체를 삭제할 예정"이라고 표시합니다.
    await db.delete(db_task)

    # commit()을 해야 DELETE SQL이 실제 DB에 반영됩니다.
    await db.commit()

    print(f"User '{current_user.email}' deleted task ID: {task_id}")

    # 204 No Content 응답은 본문이 없는 성공 응답입니다.
    # 그래서 삭제가 성공하면 별도 데이터를 반환하지 않습니다.
    return None
