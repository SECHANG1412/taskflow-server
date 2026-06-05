from passlib.context import CryptContext


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
