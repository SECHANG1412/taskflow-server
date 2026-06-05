from os import access
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import get_db
from ..sql_models.user import User as SQLAlchemyUser
from ..schemas.token import Token
from ..security import verify_password, create_access_token 

# 이 파일은 "로그인"을 담당하는 라우터입니다.
# 회원가입은 users.py에서 처리하고,
# 여기서는 이미 가입된 사용자가 이메일/비밀번호로 로그인했을 때 JWT 토큰을 발급합니다.
#
# 전체 흐름:
# 1. 클라이언트가 /token 으로 username, password를 보냅니다.
# 2. 서버가 username을 이메일처럼 사용해서 DB에서 사용자를 찾습니다.
# 3. 입력한 비밀번호와 DB의 해시 비밀번호를 비교합니다.
# 4. 맞으면 JWT access token을 만들어서 돌려줍니다.



# 인증 관련 라우터 생성
router = APIRouter()



# '/token' 경로로 POST 요청을 받아 로그인을 처리하고 토큰을 발급합니다.
# 사용자 이메일(폼 데이터의 'username' 필드)과 비밀번호를 사용하여 인증하고, 성공 시 JWT 액세스 토큰을 반환합니다.
@router.post("/token", response_model=Token, summary="Get access token")
async def login_for_access_token(

    # OAuth2PasswordRequestForm:
    # 로그인 요청에서 username, password 값을 꺼내주는 FastAPI 도구입니다.
    
    # Swagger의 Authorize 버튼이나 OAuth2 방식에서는 JSON이 아니라 form-data 방식으로 username/password를 보냅니다.
    form_data: OAuth2PasswordRequestForm = Depends(),   # 폼 데이터(username, password) 주입
    db: AsyncSession = Depends(get_db)                  # DB 세션 주입
):
    

    # 1. 데이터베이스에서 사용자 조회 (폼 데이터의 username을 이메일로 사용)

    # select(SQLAlchemyUser):
    # users 테이블에서 User 데이터를 조회하겠다는 SELECT 명령서를 만듭니다.

    # where(SQLAlchemyUser.email == form_data.username):
    # DB의 email 컬럼이 로그인 폼의 username 값과 같은 사용자만 찾겠다는 조건입니다.
    # 즉, "이 이메일로 가입한 사용자가 있나?"를 확인하는 코드입니다.
    query = select(SQLAlchemyUser).where(SQLAlchemyUser.email == form_data.username)

    # db.execute(query):
    # 위에서 만든 SELECT 명령서를 실제 DB에 보내서 실행합니다.
    # result에는 DB가 돌려준 조회 결과가 들어갑니다.
    result = await db.execute(query)

    # scalar_one_or_none:
    # 조회 결과에서 User 객체 하나만 꺼내기 위한 메서드입니다.
    # 사용자가 있으면 User 객체, 없으면 None을 기대합니다.
    user = result.scalar_one_or_none


    # 2. 사용자가 없거나 비밀번호가 틀린 경우 인증 실패 처리
    # (보안을 위해 "이메일 또는 비밀번호 오류" 처럼 일반적인 메시지 사용)
    
    # not user:
    # 해당 이메일로 가입된 사용자가 없다는 뜻입니다.

    # verify_password(form_data.password, user.hashed_password):
    # 사용자가 방금 입력한 원본 비밀번호와 DB에 저장된 해시 비밀번호가 서로 맞는지 검사합니다.

    # 둘 중 하나라도 실패하면 로그인 실패입니다.
    if not user or not verify_password(form_data.password, user.hashed_password):
        print(f"Login failed for email: {form_data.username}")
        raise HTTPException(
            # 401 Unauthorized:
            # "로그인이 필요하거나, 인증 정보가 틀렸다"는 의미의 HTTP 상태 코드입니다.
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",

            # WWW-Authenticate: Bearer:
            # 클라이언트에게 "Bearer 토큰 방식으로 인증해야 한다"고 알려주는 헤더입니다.
            headers={"WWW-Authenticate": "Bearer"},
        )
    



    # 3. 인증 성공! JWT 페이로드 생성 (사용자 식별 정보 포함)
    # 'sub' (subject) 클레임은 토큰의 주체를 나타내며, 보통 사용자 ID나 이메일을 사용합니다.
    
    # access_token_data:
    # JWT 안에 넣을 내용입니다.

    # sub:
    # subject의 줄임말입니다. 쉽게 말해 "이 토큰은 누구의 토큰인가?"를 나타냅니다.

    # 여기서는 로그인한 사용자의 email을 토큰의 주인 정보로 넣습니다.
    access_token_data = {"sub": user.email}





    # 4. 액세스 토큰 생성 (유효 기간 적용됨)

    # create_access_token:
    # access_token_data에 만료 시간(exp)을 붙이고, SECRET_KEY로 서명해서 JWT 문자열을 만들어줍니다.

    # 이 access_token이 클라이언트가 앞으로 API 요청할 때 들고 다닐 로그인 증명서입니다.
    access_token = create_access_token(data=access_token_data)

    print(f"User {user.email} logged in successfully.")




    # 5. OAuth2 표준 형식으로 토큰 반환
    # response_model=Token 에 의해 JSON으로 직렬화됩니다.
    
    # OAuth2 표준 응답 형식:
    # access_token에는 실제 JWT 문자열을 넣습니다.
    # token_type은 보통 "bearer"를 사용합니다.

    # 클라이언트는 이후 요청에서 아래처럼 사용합니다.
    # Authorization: Bearer <access_token>
    return {"access_token": access_token, "token_type": "bearer"}
