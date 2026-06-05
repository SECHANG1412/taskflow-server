import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

# os:
# 환경 변수에서 SECRET_KEY 같은 설정값을 가져오기 위해 사용합니다.
#
# datetime, timedelta, timezone:
# JWT 토큰에 "언제 만료되는지"를 넣기 위해 사용합니다.
# 예: 지금 시간 + 30분 = 토큰 만료 시간
#
# Optional:
# expires_delta 값이 들어올 수도 있고, 안 들어올 수도 있다는 뜻을 표현합니다.
#
# jose.jwt:
# JWT 토큰을 실제로 만들어주는 도구입니다.
# 사용자 정보 + 만료 시간을 SECRET_KEY로 서명해서 문자열 토큰으로 바꿔줍니다.
#
# OAuth2PasswordBearer:
# 나중에 Authorization: Bearer <token> 헤더에서 토큰만 꺼내기 위해 사용합니다.


# --- 비밀번호 해싱 설정 ---
# 사용할 해싱 스키마 지정 (bcrypt 권장), deprecated="auto"는 이전 형식 자동 감지/업데이트 지원
# schemes=["bcrypt"]는 비밀번호를 bcrypt 방식으로 해싱하겠다는 뜻입니다.
# deprecated="auto"는 오래된 해시 방식이 있으면 passlib가 자동으로 판단하게 합니다.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")




# --- 비밀번호 검증 함수 ---
# 입력된 비밀번호와 해시된 비밀번호가 일치하는지 확인
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 로그인할 때 사용합니다.
    # plain_password는 사용자가 방금 입력한 원본 비밀번호입니다.
    # hashed_password는 DB에 저장되어 있던 해시된 비밀번호입니다.
    # 둘이 같은 비밀번호에서 나온 값이면 True, 아니면 False를 반환합니다.
    return pwd_context.verify(plain_password, hashed_password)




# --- 비밀번호 해싱 함수 ---
# 입력된 비밀번호를 해싱하여 반환
def get_password_hash(password: str) -> str:
    # 회원가입할 때 사용합니다.
    # 사용자가 입력한 원본 비밀번호를 DB에 그대로 저장하지 않고, 
    # bcrypt 해시 문자열로 바꿔서 저장하기 위해 사용합니다.
    return pwd_context.hash(password)



# --- ✨ JWT 설정 ✨ ---
# !!! 보안 경고: 실제 환경에서는 절대 코드에 직접 작성하지 마세요!
# 환경 변수나 .env 파일, 보안 관리 도구를 사용하세요.
# 예: 터미널에서 'openssl rand -hex 32' 실행하여 강력한 키 생성
# SECRET_KEY:
# JWT에 찍는 서버 전용 도장 같은 값입니다.
# 서버는 이 값으로 토큰을 만들고, 나중에 같은 값으로 "우리 서버가 만든 토큰이 맞는지" 확인합니다.
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_in_env_var_or_secret_manager_0123456789abcdef")

# ALGORITHM:
# JWT에 도장을 찍을 때 사용할 서명 방식입니다.
# HS256은 SECRET_KEY 하나로 토큰 생성과 검증을 둘 다 하는 방식입니다.
ALGORITHM = "HS256"              # 사용할 서명 알고리즘 (HS256은 HMAC using SHA-256)
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # 액세스 토큰 유효 기간 (분 단위)



# --- ✨ OAuth2 Password Bearer 스키마 설정 ✨ ---
# tokenUrl은 클라이언트가 사용자 이름과 비밀번호를 보내 토큰을 요청할 엔드포인트의 *상대* 경로입니다.
# 예: "/token" -> 실제 URL은 http://<your_domain>/token
# oauth2_scheme:
# 보호된 API에서 Authorization 헤더에 담긴 Bearer 토큰을 꺼내기 위한 도구입니다.
#
# 예:
# Authorization: Bearer abc.def.ghi
#
# 이 도구는 위 헤더에서 abc.def.ghi 부분만 꺼내줍니다.
# tokenUrl="token"은 Swagger 문서에 "토큰은 /token에서 받아라"라고 알려주는 설정입니다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



# --- ✨ JWT 생성 함수 ✨ ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # data:
    # JWT 안에 넣고 싶은 사용자 정보입니다.
    # 보통 {"sub": user.email}처럼 "이 토큰의 주인이 누구인지"를 넣습니다.
    #
    # expires_delta:
    # 토큰 유효 시간을 직접 지정하고 싶을 때 사용합니다.
    # 값이 없으면 ACCESS_TOKEN_EXPIRE_MINUTES 기준으로 기본 만료 시간을 사용합니다.


    # 원본 data를 바로 수정하지 않기 위해 복사본을 만듭니다.
    # 이 복사본에 exp 같은 JWT 전용 정보를 추가해서 토큰으로 바꿉니다.
    to_encode = data.copy()
    


    # expires_delta가 들어오면:
    # "현재 UTC 시간 + 직접 지정한 시간"을 만료 시간으로 사용합니다.
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        

    # expires_delta가 없으면:
    # "현재 UTC 시간 + 기본 설정 시간(30분)"을 만료 시간으로 사용합니다.
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # JWT 안에 exp를 추가합니다.
        # exp는 expiration time의 줄임말로, "이 토큰은 이 시간 이후로 만료된다"는 뜻입니다.
        to_encode.update({"exp": expire})
        

        # to_encode에 담긴 정보를 SECRET_KEY와 ALGORITHM으로 서명해서 JWT 문자열을 만듭니다.
        # 이 결과가 클라이언트에게 전달되는 access_token입니다.
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        

        # 완성된 JWT 토큰 문자열을 반환합니다.
        return encoded_jwt
        
