# Dockerfile

# 1. 베이스 이미지 설정: 공식 Python 런타임을 부모 이미지로 사용합니다.
# slim 버전을 사용하면 이미지 크기를 줄일 수 있습니다. 개발 환경과 버전을 맞춥니다.
FROM python:3.12-slim

# 2. 작업 디렉토리 설정: 컨테이너 내부에서 명령이 실행될 기본 디렉토리를 지정합니다.
WORKDIR /code

# 3. 의존성 설치:
# 먼저 requirements.txt 파일만 복사합니다. (Docker 레이어 캐싱 활용!)
COPY requirements.txt requirements.txt
# pip를 사용하여 의존성 라이브러리들을 설치합니다.
# --no-cache-dir: 불필요한 캐시를 저장하지 않아 이미지 크기를 줄입니다.
# --upgrade: pip 자체 및 라이브러리들을 최신 버전으로 설치하도록 시도합니다.
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 4. 애플리케이션 코드 복사: 로컬의 ./app 디렉토리 내용을 컨테이너의 /code/app 디렉토리로 복사합니다.
# (Alembic 사용 시 ./alembic 과 alembic.ini 도 복사 필요할 수 있음 - 추후 고려)
COPY ./app /code/app

# 5. 포트 노출: 컨테이너가 런타임에 8000번 포트를 리스닝할 것임을 Docker에 알립니다.
# (실제로 포트를 외부에 게시하는 것은 'docker run -p' 옵션입니다.)
EXPOSE 8000

# 6. 애플리케이션 실행 명령: 컨테이너가 시작될 때 실행될 기본 명령입니다.
# Uvicorn을 사용하여 FastAPI 앱을 실행합니다.
# --host 0.0.0.0 : 컨테이너 외부(호스트 머신 등)에서의 연결을 허용하기 위해 필수!
# --port 8000 : 8000번 포트에서 실행
# 'app.main:app' : app 패키지의 main 모듈 안에 있는 app FastAPI 인스턴스를 의미합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]