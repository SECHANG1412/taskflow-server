import asyncio
import time
from token import OP
from fastapi import FastAPI, BackgroundTasks, Depends
from typing import Optional


app = FastAPI()


###################################################
# 백그라운드에서 실행할 함수들
###################################################

# 알림 기록을 파일에 남기는 동기 함수입니다.
def write_notification_log(email: str, message: str = ""):

    # 로그 파일에 저장할 한 줄짜리 문자열을 만듭니다.
    # time.strftime()은 현재 시간을 "연-월-일 시:분:초" 형태의 문자열로 바꿔줍니다.
    log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Notification to {email}: {message}\\n"

    # 실제 파일에 쓰기 전에 콘솔에도 한 번 출력해서 동작을 확인합니다.
    print(f"Background Task (sync): Writing log - {log_entry.strip()}")

    try: 
        # notification_log.txt 파일을 append 모드로 엽니다.
        # append 모드는 기존 내용을 지우지 않고 파일 맨 아래에 새 내용을 추가합니다.
        with open("notification_log.txt", mode="a") as log_file:
            log_file.write(log_entry)

    except Exception as e:
        # 파일 쓰기 중 문제가 생겨도 서버 전체가 죽지 않도록 예외를 잡습니다.
        # 실제 서비스라면 이 에러도 별도 로깅 시스템에 남기는 것이 좋습니다.
        print(f"Background Task Error (write_log): {e}")


# 이 함수는 BackgroundTasks에 등록될 "동기 백그라운드 작업" 예제입니다.
# 중요한 점은 이 함수가 API 응답을 만들기 전에 바로 실행되는 것이 아니라,
# background_tasks.add_task(...)로 등록된 뒤 응답이 나간 다음 실행된다는 것입니다.
# 여기서는 단순히 로그 파일에 내용을 쓰지만, 실제 서비스에서는 짧은 로그 기록이나 알림 기록 같은 작업에 사용할 수 있습니다.


# 이메일 전송을 흉내 내는 비동기 함수입니다.
async def send_email_async(email: str, subject: str, body: str):

    # 실제 이메일을 보내는 대신, 콘솔에 이메일 전송이 시작됐다고 출력합니다.
    print(f"Background Task (async): Sending email to {email}...")
    print(f"Subject: {subject}")

    # 실제 이메일 전송은 네트워크 I/O 작업이라 시간이 걸릴 수 있습니다.
    # 여기서는 asyncio.sleep(3)으로 "이메일 전송에 3초 걸리는 상황"을 흉내 냅니다.
    # asyncio.sleep()은 이벤트 루프를 막지 않는 비동기 대기입니다.
    await asyncio.sleep(3)

    # 3초 대기가 끝나면 이메일이 전송된 것처럼 출력합니다.
    print(f"Background Task (async): Email supposedly sent to {email}")


# 이 함수는 BackgroundTasks에 등록될 "비동기 백그라운드 작업" 예제입니다.
# FastAPI의 BackgroundTasks에는 일반 def 함수도 넣을 수 있고, async def 함수도 넣을 수 있습니다.
# 이 예제에서는 이메일 전송처럼 응답 전에 꼭 끝낼 필요가 없는 작업을 백그라운드로 미룹니다.
# 사용자는 이메일 전송이 끝날 때까지 기다리지 않고, 먼저 "처리 시작됨" 응답을 받을 수 있습니다.





###################################################
# BackgroundTasks 사용 예제 엔드포인트
###################################################

# 이메일 알림 작업을 백그라운드에 등록하고, 클라이언트에게는 먼저 응답합니다.
@app.post("/send-email/{email}")
async def send_email_notifocation(
    email: str,
    message: str,
    background_tasks: BackgroundTasks
):
    
    # email은 URL 경로에서 받은 값입니다.
    # 예: POST /send-email/test@example.com
    #
    # message는 쿼리 파라미터 또는 요청 데이터로 들어오는 알림 메시지입니다.
    #
    # background_tasks는 FastAPI가 자동으로 넣어주는 BackgroundTasks 객체입니다.
    # 여기에 add_task()로 함수를 등록하면, FastAPI가 응답을 보낸 뒤 그 함수를 실행합니다.

    # 이메일 제목을 만듭니다.
    subject = f"Notification for {email}"

    # 첫 번째 백그라운드 작업을 등록합니다.
    # 응답이 나간 뒤 send_email_async(email, subject, message)가 실행됩니다.
    # 즉, 이메일 보내는 일을 지금 바로 기다리지 않고 뒤로 미룹니다.
    background_tasks.add_task(send_email_async, email, subject, message)

    # 두 번째 백그라운드 작업을 등록합니다.
    # 이메일 전송 작업을 등록했다는 사실을 로그 파일에 남깁니다.
    background_tasks.add_task(write_notification_log, email, f"Email sending task added for subject: {subject}")

    # 이 print는 백그라운드 작업이 끝난 뒤가 아니라, 응답을 반환하기 직전에 실행됩니다.
    # 즉, 이 시점에는 이메일 전송이 완료된 것이 아니라 "예약된 상태"입니다.
    print(f"Main task: Returning response for email to {email}. Background tasks scheduled.")

    # 클라이언트에게 즉시 응답합니다.
    # 이메일 전송과 로그 기록은 이 응답이 나간 뒤 백그라운드에서 실행됩니다.
    return {"message": "Notification sending process initiated in the background"}


# 이 엔드포인트의 핵심 흐름은 다음과 같습니다.
# 요청이 들어오면 서버는 이메일 작업과 로그 작업을 BackgroundTasks에 등록합니다.
# 그다음 클라이언트에게 "백그라운드에서 처리 시작됨"이라는 응답을 먼저 보냅니다.
# 응답이 끝난 뒤 FastAPI가 등록된 send_email_async()와 write_notification_log()를 실행합니다.
# 그래서 사용자는 이메일 전송 3초를 기다리지 않고 빠르게 응답을 받을 수 있습니다.


# 다른 의존성과 BackgroundTasks를 함께 사용할 수 있음을 보여주는 간단한 의존성 함수입니다.
def get_query(q: Optional[str] = None):
    # q라는 선택적 쿼리 파라미터를 그대로 반환합니다.
    # 예: /items/?item_id=1&item_name=book&q=test
    return q


# 아이템을 생성하고, 생성 로그 기록은 백그라운드로 미루는 예제입니다.
@app.post("/items/")
async def create_item(
    item_id: int,
    item_name: str,
    background_tasks: BackgroundTasks,
    q: Optional[str] = Depends(get_query)
):
    # item_id와 item_name은 클라이언트가 보낸 아이템 정보입니다.
    # background_tasks는 응답 후 실행할 작업을 등록하는 객체입니다.
    # q는 get_query 의존성 함수에서 가져온 선택적 쿼리 값입니다.

    print(f"Main task: Creating item {item_id} - {item_name}")

    # 실제 서비스라면 여기서 DB에 아이템을 저장할 수 있습니다.
    # 이 예제에서는 DB 저장 대신 딕셔너리로 아이템 데이터를 만든 것처럼 처리합니다.
    item_data = {"id": item_id, "name": item_name}

    # 백그라운드 로그에 남길 메시지를 만듭니다.
    log_message = f"Item created: id={item_id}, name='{item_name}'"

    # q 값이 있으면 로그 메시지에 q 정보도 추가합니다.
    if q:
        log_message += f", query='{q}"

    # 아이템 생성 로그를 백그라운드 작업으로 등록합니다.
    # 이 함수는 응답 전에 바로 실행되는 것이 아니라, 응답이 나간 뒤 실행됩니다.
    background_tasks.add_task(write_notification_log, "admin@example.com", log_message)

    # 여기까지 왔다는 것은 아이템 생성 응답을 보낼 준비가 끝났다는 뜻입니다.
    # 로그 기록은 예약만 해두었고, 실제 파일 쓰기는 응답 후에 실행됩니다.
    print("Main task: Returning response for item creation.")

    # 클라이언트에게는 아이템 생성 성공 응답을 먼저 보냅니다.
    return {"item": item_data, "message": "Item created successfully, logging in background."}


# 이 엔드포인트는 BackgroundTasks가 다른 Depends 의존성과 함께 사용될 수 있다는 것을 보여줍니다.
# FastAPI는 background_tasks도 주입하고, q도 get_query를 통해 주입합니다.
# 중요한 작업인 "아이템 생성 응답"은 바로 처리하고,
# 덜 급한 작업인 "생성 로그 기록"은 백그라운드로 미룹니다.
# BackgroundTasks는 이런 식으로 응답 시간을 줄이고 사용자 경험을 좋게 만드는 데 사용할 수 있습니다.
