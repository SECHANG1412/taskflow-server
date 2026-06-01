from pydantic import BaseModel, Field
from typing import Optional

class TaskBase(BaseModel):
    # TaskCreate와 Task가 공통으로 사용할 기본 필드입니다.
    # title은 필수값이고, 1~100글자 사이여야 합니다.
    # description은 선택값이고, 입력한다면 최대 500글자까지 허용합니다.
    title: str = Field(..., min_length=1, max_length=100, description="할 일 제목 (1~100자)")
    description: Optional[str] = Field(default=None, max_length=500, description="상세 설명 (최대 500자)")

    model_config = { # Pydantic V2 설정
        # model_config는 Pydantic 모델의 추가 설정을 적는 곳입니다.
        # 여기서는 API 문서에 보여줄 예시 데이터를 설정합니다.
        "json_schema_extra": {
            "examples": [ {"title": "장보기", "description": "우유, 계란, 파 사기"} ]
        }
    }


class TaskCreate(TaskBase):
    # 새 Task를 만들 때 클라이언트가 보내는 요청 모델입니다.
    # 현재는 TaskBase와 필드가 같기 때문에 별도 필드를 추가하지 않습니다.
    pass


# 할 일 응답 또는 내부 표현 모델
class Task(TaskBase):
    # 서버가 응답으로 돌려주는 Task 모델입니다.
    # TaskBase 필드에 서버가 관리하는 id와 completed 값을 추가합니다.
    id: int = Field(..., description="고유 Task ID")
    completed: bool = Field(default=False, description="완료 여부")

    model_config = { # Pydantic V2 설정
        # model_config는 Pydantic 모델의 추가 설정을 적는 곳입니다.
        # 여기서는 API 문서에 보여줄 예시 데이터를 설정합니다.
        "json_schema_extra": {
            "examples": [
                { "id": 1, "title": "FastAPI 공부하기", "description": "17강 프로젝트 구조화 완료하기", "completed": False }
            ]
        }
    }
