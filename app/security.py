import os
from datetime import datetime, timedelta, timezone
from sqlite3 import SQLITE_LIMIT_ATTACHED
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .database import get_db
from .sql_models.user import User as SQLAlchemyUser

from .schemas.token import TokenData


# 비밀번호 해싱과 검증에 사용할 passlib 설정입니다.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 여기서 pwd_context는 비밀번호 전용 보안 도구라고 보면 됩니다.
# 회원가입할 때는 사용자가 입력한 원본 비밀번호를 bcrypt 해시 문자열로 바꿉니다.
# 로그인할 때는 사용자가 다시 입력한 원본 비밀번호가 DB에 저장된 해시와 맞는지 확인합니다.
# bcrypt는 비밀번호 저장에 자주 쓰이는 안전한 해싱 방식입니다.
# deprecated="auto"는 나중에 오래된 해싱 방식이 섞였을 때 passlib가 자동으로 판단할 수 있게 해주는 설정입니다.



# 로그인 때 입력한 원본 비밀번호와 DB의 해시 비밀번호가 맞는지 확인합니다.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # plain_password는 사용자가 로그인 화면에서 방금 입력한 원본 비밀번호입니다.
    # hashed_password는 회원가입 때 해싱되어 DB에 저장된 비밀번호 문자열입니다.
    # 원본 비밀번호끼리 비교하는 것이 아니라, passlib가 해시 규칙을 이용해 같은 비밀번호인지 검사합니다.
    # 결과가 맞으면 True, 틀리면 False를 반환합니다.
    return pwd_context.verify(plain_password, hashed_password)





# 회원가입 때 받은 원본 비밀번호를 DB 저장용 해시 문자열로 바꿉니다.
def get_password_hash(password: str) -> str:
    # 사용자의 비밀번호를 그대로 DB에 저장하면 매우 위험합니다.
    # 그래서 회원가입 시점에 이 함수를 사용해서 비밀번호를 bcrypt 해시 문자열로 바꿉니다.
    # DB에는 "1234" 같은 원본 비밀번호가 아니라, bcrypt가 만든 긴 해시 문자열만 저장됩니다.
    # 나중에 로그인할 때는 verify_password()로 원본 비밀번호와 이 해시가 맞는지 검사합니다.
    return pwd_context.hash(password)



# --- JWT 설정 ---
# ✨ 환경 변수에서 SECRET_KEY 읽어오기 ✨

# JWT를 만들고 검증할 때 사용할 기본 설정입니다.
SECRET_KEY = os.getenv("SECRET_KEY", "please_change_this_default_secret_key")
ALGORITHM = "HS256"

# ✨ 환경 변수에서 만료 시간 읽어오기 (숫자 타입 변환 필요) ✨
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# SECRET_KEY는 서버만 알고 있어야 하는 비밀값입니다.
# JWT는 이 값으로 서명되기 때문에, 서버는 나중에 토큰을 보고 "내가 만든 토큰이 맞다"라고 확인할 수 있습니다.
# 실제 서비스에서는 SECRET_KEY를 코드에 직접 적지 않고 .env나 서버 환경 변수로 관리합니다.

# ALGORITHM은 JWT 서명에 사용할 방식입니다.
# HS256은 SECRET_KEY 하나로 토큰 생성과 검증을 둘 다 처리하는 방식입니다.

# ACCESS_TOKEN_EXPIRE_MINUTES는 로그인 토큰을 몇 분 동안만 사용할 수 있게 할지 정하는 값입니다.
# 현재 값이 30이므로, 기본 토큰 만료 시간은 30분입니다.





# 요청 헤더에서 Bearer 토큰을 꺼내기 위한 FastAPI 보안 도구입니다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 클라이언트가 보호된 API에 접근할 때는 보통 아래 형태로 토큰을 보냅니다.
# Authorization: Bearer <JWT토큰값>

# oauth2_scheme은 이 Authorization 헤더에서 실제 JWT 토큰 문자열만 꺼내줍니다.
# 여기서 토큰이 맞는지 검증하는 것은 아닙니다.
# 토큰 검증은 아래 get_current_user() 함수에서 jwt.decode()로 처리합니다.

# tokenUrl="token"은 Swagger 문서에 알려주는 로그인 주소입니다.
# Swagger의 Authorize 기능은 이 값을 보고 "/token으로 로그인해서 토큰을 받으면 되는구나"라고 알 수 있습니다.





# 로그인 성공 후 클라이언트에게 줄 JWT access token을 만듭니다.
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # data에는 JWT 안에 넣고 싶은 정보가 들어옵니다.
    # 보통 {"sub": user.email}처럼 "이 토큰의 주인이 누구인지"를 나타내는 정보를 넣습니다.
    # 원본 data를 직접 수정하지 않기 위해 copy()로 복사본을 만듭니다.
    to_encode = data.copy()

    # expires_delta가 들어오면, 호출한 쪽에서 직접 지정한 유효 시간을 사용합니다.
    # 예를 들어 expires_delta가 10분이면 현재 시간에서 10분 뒤를 만료 시간으로 잡습니다.
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta

    # expires_delta가 없으면 기본 설정값인 ACCESS_TOKEN_EXPIRE_MINUTES를 사용합니다.
    # 현재 설정에서는 기본 만료 시간이 30분입니다.
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # JWT 표준에서 exp는 expiration time, 즉 토큰 만료 시간을 뜻합니다.
        # 이 값이 들어가야 서버가 나중에 토큰을 검증할 때 "아직 유효한 토큰인가?"를 판단할 수 있습니다.
        to_encode.update({"exp": expire})

        # jwt.encode()는 딕셔너리 데이터를 JWT 문자열로 바꿔줍니다.
        # 이때 SECRET_KEY와 ALGORITHM을 사용해서 토큰에 서버의 서명을 붙입니다.
        # 이 서명 덕분에 서버는 나중에 토큰이 위조되지 않았는지 확인할 수 있습니다.
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        # 최종적으로 만들어진 JWT 문자열을 반환합니다.
        # 클라이언트는 이 값을 access_token으로 받아 저장하고, 이후 요청에 Bearer 토큰으로 보냅니다.
        return encoded_jwt






# JWT 토큰을 검증하고, 현재 요청을 보낸 사용자를 DB에서 찾아 반환합니다.
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> SQLAlchemyUser:
    
    # 인증 실패 때 반복해서 사용할 401 예외 객체입니다.
    # 토큰이 없거나, 토큰이 잘못됐거나, 만료됐거나, 사용자를 찾지 못하면 이 예외를 발생시킵니다.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # token은 oauth2_scheme이 Authorization 헤더에서 꺼내준 JWT 문자열입니다.
    # db는 get_db가 만들어준 DB 세션입니다.
    # 이 함수는 먼저 토큰 자체를 검증하고, 그다음 토큰 안의 이메일로 DB에서 사용자를 찾습니다.

    try:
        # jwt.decode()는 토큰을 해석하면서 동시에 검증합니다.
        # SECRET_KEY가 다르면 위조된 토큰으로 판단하고 실패합니다.
        # exp 만료 시간이 지났어도 실패합니다.
        # 검증에 성공하면 payload라는 딕셔너리가 나옵니다.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # sub는 subject의 줄임말입니다.
        # 여기서는 "이 토큰의 주인이 누구인가?"를 나타내는 값으로 이메일을 사용합니다.
        email: str = payload.get("sub")

        # sub가 없으면 토큰은 있어도 누구의 토큰인지 알 수 없습니다.
        # 그래서 인증 실패로 처리합니다.
        if email is None:
            print("JWT 'sub' claim missing")
            raise credentials_exception

        # 토큰에서 꺼낸 이메일을 TokenData 스키마로 한 번 감싸 검증합니다.
        # 이렇게 하면 이후 코드에서 token_data.email처럼 명확하게 사용할 수 있습니다.
        token_data = TokenData(email=email)

    except JWTError as e:
        # JWTError는 토큰 검증 중 문제가 생겼을 때 발생합니다.
        # 예를 들어 토큰이 위조됐거나, 형식이 잘못됐거나, 만료된 경우입니다.
        print(f"JWT Error during decoding: {e}")
        raise credentials_exception
    

    # 토큰 자체가 유효하더라도, DB에 해당 사용자가 실제로 존재하는지 다시 확인해야 합니다.
    # 예를 들어 사용자가 탈퇴했는데 예전 토큰으로 요청할 수도 있기 때문입니다.
    query = select(SQLAlchemyUser).where(SQLAlchemyUser.email == token_data.email)

    # 위에서 만든 SELECT 쿼리를 실제 DB에 실행합니다.
    result = await db.execute(query)

    # 조회 결과에서 사용자 한 명을 꺼냅니다.
    # 사용자가 있으면 User 객체, 없으면 None이 됩니다.
    user = result.scalar_one_or_none

    # DB에서 사용자를 찾지 못하면 인증 실패로 처리합니다.
    # 토큰 안의 이메일이 정상이어도, 현재 DB에 없는 사용자라면 API를 사용할 수 없습니다.
    if user is None:
        print(f"User not found in DB for email from token: {token_data.email}")
        raise credentials_exception

    # 여기까지 왔다는 것은 토큰도 유효하고, DB에 사용자도 존재한다는 뜻입니다.
    # tasks.py 같은 보호된 API에서는 이 반환값을 current_user로 받아 사용합니다.
    return user









# 관리자 권한이 필요한 API에서 사용할 의존성 함수입니다.
async def require_admin(
        current_user: SQLAlchemyUser = Depends(get_current_user)
) -> SQLAlchemyUser:
    
    # current_user는 get_current_user()를 통해 가져온 현재 로그인 사용자입니다.
    # 즉, 이 함수가 실행된다는 것은 이미 JWT 토큰 검증은 통과했다는 뜻입니다.
    # 여기서는 "로그인한 사용자인가?"가 아니라 "관리자 권한이 있는 사용자인가?"를 추가로 확인합니다.

    if not current_user.is_admin: 
        print(f"Forbidden: User '{current_user.email}' is not an admin.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )

        # current_user.is_admin이 False라면 일반 사용자입니다.
        # 일반 사용자는 관리자 전용 API를 실행할 권한이 없으므로 403 Forbidden을 반환합니다.
        # 401 Unauthorized는 "로그인이 안 됐거나 토큰이 이상하다"는 뜻이고,
        # 403 Forbidden은 "누구인지는 알겠지만 이 작업을 할 권한은 없다"는 뜻입니다.
    
    return current_user

    # 여기까지 통과했다는 것은 현재 사용자가 로그인도 되어 있고, 관리자 권한도 있다는 뜻입니다.
    # 관리자 전용 라우터에서는 이 함수를 Depends(require_admin) 형태로 붙여서 사용합니다.
    # 그러면 FastAPI가 실제 API 함수를 실행하기 전에 먼저 관리자 여부를 검사합니다.
