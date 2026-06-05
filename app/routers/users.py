import email
from opcode import hasexc
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Pydantic 모델 임포트
# User 는 Pydantic 모델
from ..models.user import User as PydanticUser, UserCreate

# SQLAlchemy 모델 임포트
# User 는 SQLAlchemy 모델
from ..sql_models.user import User as SQLAlchemyUser

# DB 세션 의존성 임포트
from ..database import get_db

# 비밀번호 해싱 함수 임포트
from ..security import get_password_hash




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
