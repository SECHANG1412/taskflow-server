import re
from fastapi import APIRouter, HTTPException, status, Path, Depends 
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.future import select 
from ..models.task import Task as PydanticTask, TaskCreate 
from ..sql_models.task import Task as SQLAlchemyTask 
from ..database import get_db
from app.models import task


# 이 라우터는 더 이상 딕셔너리(tasks_db)를 쓰지 않습니다.
# get_db로 받은 DB session을 이용해서 실제 데이터베이스에 CRUD 작업을 합니다.
router = APIRouter()



# --- ORM을 사용한 Task CRUD 구현 ---

# 1. Create Task (생성)
# 새로운 할 일을 생성하고 데이터베이스에 저장합니다.
@router.post("/", response_model=PydanticTask, status_code=status.HTTP_201_CREATED, summary="Create a new task")
async def create_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db)):

    # 1. SQLAlchemy 모델 객체 생성 (Pydantic 모델 데이터 사용)
    # Pydantic 모델은 API 요청/응답용이고, SQLAlchemy 모델은 DB 저장용입니다.
    # model_dump()로 Pydantic 객체를 dict로 바꾼 뒤 SQLAlchemyTask 객체를 만듭니다.
    db_task = SQLAlchemyTask(**task_in.model_dump())

    # 2. 세션에 객체 추가 (아직 DB에 저장된 것 아님)
    # add()는 "이 객체를 저장할 예정"이라고 session에 등록하는 단계입니다.
    db.add(db_task)

    # 3. 변경사항을 데이터베이스에 커밋 (실제 INSERT 발생)
    # commit()을 해야 INSERT가 실제 DB에 확정됩니다.
    await db.commit()

    # 4. DB에 의해 생성된 값(예: id)을 객체에 반영
    # refresh()는 DB가 자동으로 만든 id 같은 최신 값을 db_task 객체에 다시 채워줍니다.
    await db.refresh(db_task)

    print(f"Task created in DB: {db_task}")

    # 5. 생성된 SQLAlchemy 객체 반환 (response_model=PydanticTask 에 의해 변환됨)
    return db_task





# 2. Read Tasks (목록 조회)
# 모든 할 일 목록을 데이터베이스에서 조회합니다. (페이징 가능)
@router.get("/", response_model=List[PydanticTask], summary="Get all tasks")
async def read_tasks(
    skip: int = 0,      # 페이징을 위한 쿼리 파라미터 (선택)
    limit: int = 100,   # 페이징을 위한 쿼리 파라미터 (선택)
    db: AsyncSession = Depends(get_db)
):
    
    # 1. SELECT 쿼리 생성 (SQLAlchemyTask 모델의 모든 컬럼 선택)
    # OFFSET 과 LIMIT 추가
    # select(SQLAlchemyTask)는 task 테이블에서 Task들을 조회하겠다는 SELECT 문입니다. -> 처음부터 시작해서 최대 100개 가져와라
    query = select(SQLAlchemyTask).offset(skip).limit(limit)
    
    # 2. 쿼리 실행
    # execute()가 실제로 SELECT 문을 DB에 보냅니다.
    result = await db.execute(query)

    # 3. 결과에서 SQLAlchemyTask 객체 리스트 추출
    # scalars() 는 각 행의 첫 번째 요소(여기서는 Task 객체)만 가져옴
    # scalars().all()은 조회 결과에서 SQLAlchemyTask 객체들만 리스트로 꺼냅니다.
    tasks = result.scalars().all()

    print(f"Reading all tasks (limit={limit}, skip={skip}) - Found {len(tasks)} items")

    # 4. SQLAlchemyTask 객체 리스트 반환 (response_model 에 의해 PydanticTask 리스트로 변환)
    return tasks





# 3. Read Task (상세 조회)
# 주어진 ID에 해당하는 특정 할 일을 데이터베이스에서 조회합니다.
@router.get("/{task_id}", response_model=PydanticTask, summary="Get a specific task by ID")
async def read_task(
    task_id: int = Path(..., title="조회할 Task의 ID", ge=1),
    db: AsyncSession = Depends(get_db)
):
    
    # 1. session.get() 을 사용하여 Primary Key 로 효율적 조회
    # SQLAlchemyTask 모델과 찾을 ID를 전달
    # get(Model, id)는 primary key 기준으로 데이터 하나를 빠르게 찾습니다.
    task = await db.get(SQLAlchemyTask, task_id)

    # 2. 결과가 없으면 404 오류 발생
    if task is None:
        print(f"Task not found for ID: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with ID {task_id} not found"
        )
    
    print(f"Reading task from DB: {task}")

    # 3. 조회된 SQLAlchemyTask 객체 반환 (response_model 적용)
    return task





# 4. Update Task (수정)
# 주어진 ID에 해당하는 할 일을 데이터베이스에서 수정합니다.
@router.put("/{task_id}", response_model=PydanticTask, summary="Update a task")
async def update_task(
    task_update: TaskCreate,
    task_id: int = Path(..., title="수정할 Task의 ID", ge=1),
    db: AsyncSession = Depends(get_db)
):
    
    # 1. 수정할 Task 객체 조회 (없으면 404)
    # 먼저 DB에서 수정 대상이 실제로 있는지 확인합니다.
    db_task = await db.get(SQLAlchemyTask, task_id)

    if db_task is None:
        print(f"Task not found for update: ID={task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with ID {task_id} not found"
        )


    # 2. Pydantic 모델의 데이터를 사용하여 SQLAlchemy 객체 필드 업데이트
    # task_update.model_dump(exclude_unset=True) 를 사용하면 클라이언트가 보낸 필드만 업데이트할 수도 있음 (PATCH 방식에 더 적합)
    # exclude_unset=True는 클라이언트가 실제로 보낸 필드만 dict에 담습니다.
    update_data = task_update.model_dump(exclude_unset=True)

    # setattr(db_task, key, value)는 db_task.key = value를 동적으로 실행하는 것과 같습니다.
    # 예: key가 "title"이면 db_task.title = value가 됩니다.
    for key, value in update_data.items():
        setattr(db_task, key, value)


    # 3. 세션에 변경사항 추가 (SQLAlchemy가 객체 변경을 감지하므로 명시적 add는 불필요할 수 있음)
    # 변경된 객체를 session에 다시 등록합니다.
    db.add(db_task)

    # 4. 변경사항 커밋 (실제 UPDATE 발생)
    # commit()을 해야 UPDATE가 실제 DB에 반영됩니다.
    await db.commit()

    # 5. 변경된 객체 상태 DB와 동기화 (선택적이지만 권장)
    # refresh()로 DB에 저장된 최신 상태를 다시 가져옵니다.
    await db.refresh(db_task)

    print(f"Task updated in DB: {db_task}")

    # 6. 수정된 SQLAlchemyTask 객체 반환 (response_model 적용)
    return db_task





# 5. Delete Task (삭제)
# 주어진 ID에 해당하는 할 일을 데이터베이스에서 삭제합니다.
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
async def delete_task(
    task_id: int = Path(..., title="삭제할 Task의 ID", ge=1),
    db: AsyncSession = Depends(get_db)
):
    
    # 1. 삭제할 Task 객체 조회 (없으면 404)
    db_task = await db.get(SQLAlchemyTask, task_id)

    if db_task is None:
        print(f"Task not found for deletion: ID={task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with ID {task_id} not found"
        )
    

    # 2. 세션에서 객체 삭제 요청 (아직 DB 반영 안됨)
    # delete()는 "이 객체를 삭제할 예정"이라고 session에 등록하는 단계입니다.
    await db.delete(db_task)

    # 3. 변경사항 커밋 (실제 DELETE 발생)
    # commit()을 해야 DELETE가 실제 DB에 확정됩니다.
    await db.commit()

    print(f"Task deleted from DB: ID={task_id}")


    # 4. 204 응답은 본문 없음
    return None
