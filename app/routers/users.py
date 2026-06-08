from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.user import User as PydanticUser, UserCreate
from ..sql_models.user import User as SQLAlchemyUser
from ..database import get_db
from ..security import get_password_hash, require_admin
from typing import List
from ..security import require_admin




# 사용자 관련 API를 모아두는 라우터입니다.
# main.py에서 include_router로 연결해야 실제 API로 동작합니다.
router = APIRouter()


# POST /users/  --> 회원가입 API입니다.
# 새로운 사용자를 등록합니다. 이메일은 고유해야 합니다
# 사용자가 보낸 email/password를 받아서 User를 DB에 저장합니다.
@router.post("/", response_model=PydanticUser, status_code=status.HTTP_201_CREATED, summary="Register new user")
async def register_user(
    user_in: UserCreate,                # 요청 본문은 UserCreate 모델 사용
    db: AsyncSession = Depends(get_db)  # DB 세션 주입
):
    # user_in은 클라이언트가 보낸 회원가입 요청 데이터입니다.
    # 예: {"email": "test@example.com", "password": "password123"}
    # db는 get_db가 만들어서 넘겨준 DB session입니다.
    
    # 1. 이메일 중복 확인
    # 같은 이메일로 이미 가입한 사용자가 있는지 먼저 확인합니다.
    # select(SQLAlchemyUser)는 users 테이블에서 User를 조회하겠다는 SELECT 문입니다.
    query = select(SQLAlchemyUser).where(SQLAlchemyUser.email == user_in.email)

    # 위에서 만든 SELECT 문을 실제 DB에 실행합니다.
    result = await db.execute(query)

    # 결과가 있으면 User 객체 하나를 가져오고, 없으면 None을 반환합니다.
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # 이미 같은 이메일이 있으면 회원가입을 막고 400 에러를 반환합니다.
        print(f"Registration failed: Email already exists - {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    
    # 2. 비밀번호 해싱
    # 원본 비밀번호는 절대 DB에 그대로 저장하지 않습니다.
    # get_password_hash()로 bcrypt 해시 문자열로 바꾼 뒤 저장합니다.
    hashed_password = get_password_hash(user_in.password)

    
    # 3. SQLAlchemy User 객체 생성 (해시된 비밀번호 사용!)
    # DB에 저장할 SQLAlchemy User 객체를 만듭니다.
    # password가 아니라 hashed_password만 넣는 것이 핵심입니다.
    db_user = SQLAlchemyUser(
        email=user_in.email,
        hashed_password=hashed_password
    )


    # 4. DB에 사용자 추가, 커밋, 리프레시
    db.add(db_user)             # add()는 "이 사용자를 저장할 예정"이라고 session에 등록하는 단계입니다.
    await db.commit()           # commit()을 해야 실제 INSERT가 DB에 반영됩니다.
    await db.refresh(db_user)   # refresh()는 DB가 자동 생성한 id 같은 최신 값을 db_user 객체에 다시 채워줍니다.


    print(f"User registered successfully: {db_user.email} (ID: {db_user.id})")

    
    # 5. 생성된 사용자 정보 반환 (SQLAlchemy 객체 -> Pydantic 모델 변환은 FastAPI가 자동으로)
    # response_model=PydanticUser 에 의해 비밀번호는 제외됨!
    # 응답 모델이 PydanticUser라서 hashed_password는 응답에 포함되지 않습니다.
    # 즉 DB에는 해시 비밀번호가 저장되지만, 클라이언트에게는 id/email만 보여줍니다.
    return db_user





# GET /users/all  --> 관리자 전용 사용자 전체 조회 API입니다.
# require_admin을 통과한 관리자만 모든 사용자 목록을 조회할 수 있습니다.
@router.get("/all", response_model=List[PydanticUser], summary="Get all users (Admin Only)")
async def read_all_users(
    db: AsyncSession = Depends(get_db),
    admin_user: SQLAlchemyUser = Depends(require_admin)
):
    # db는 이번 요청에서 DB 조회를 처리할 SQLAlchemy 세션입니다.
    # admin_user는 require_admin을 통과한 현재 로그인 관리자 사용자입니다.
    
    # 여기서는 get_current_user가 아니라 require_admin을 사용합니다.
    # get_current_user는 "로그인한 사용자인가?"까지만 확인합니다.
    # require_admin은 거기에 추가로 "관리자인가?"까지 확인합니다.
    # 그래서 일반 사용자가 이 API를 호출하면 403 Forbidden 에러가 발생합니다.

    print(f"Admin user '{admin_user.email}' accessing all users list.")

    # users 테이블의 모든 사용자 데이터를 조회하는 SELECT 쿼리를 만듭니다.
    # 특정 사용자만 고르는 where 조건이 없기 때문에 전체 사용자를 가져옵니다.
    query = select(SQLAlchemyUser)

    # 위에서 만든 SELECT 쿼리를 실제 DB에 실행합니다.
    # result에는 DB가 돌려준 사용자 조회 결과가 들어갑니다.
    result = await db.execute(query)

    # scalars()는 조회 결과에서 SQLAlchemyUser 객체만 꺼냅니다.
    # all()은 그 사용자 객체들을 전부 리스트로 만듭니다.
    users = result.scalars().all()

    # response_model=List[PydanticUser]가 있으므로 FastAPI가 응답을 PydanticUser 리스트 형태로 변환합니다.
    # PydanticUser 모델에 포함된 필드만 클라이언트에게 응답됩니다.
    # 보통 hashed_password 같은 민감한 값은 응답 모델에 넣지 않아서 클라이언트에게 노출되지 않게 합니다.
    return users
