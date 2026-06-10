import asyncio
import time
from fastapi import FastAPI

app = FastAPI()


####################################
# 동기 방식 예제
####################################

# 지정한 초(duration)만큼 실행을 완전히 멈추는 동기 함수입니다.
def sync_blocking_task(duration: int):
    print(f"Sync task started, will sleep for {duration} seconds...")

    # time.sleep()은 Blocking 작업입니다.
    # 이 줄이 실행되는 동안 현재 작업 흐름은 완전히 멈춥니다.
    # 예를 들어 duration이 2라면, 이 함수는 2초 동안 아무것도 하지 못하고 기다립니다.
    time.sleep(duration)

    print(f"Sync task finished after {duration} seconds.")

    return {"message": f"Synchronous task complete after {duration}s"}


# 동기 함수가 요청을 처리할 때 어떤 식으로 기다리는지 확인하는 API입니다.
@app.get("/sync-task")
def run_sync_task():

    # 시작 시간을 기록합니다. 아래 작업이 실제로 몇 초 걸렸는지 계산하기 위해 사용합니다.
    start_time = time.time()

    # sync_blocking_task(2)는 내부에서 time.sleep(2)를 실행합니다.
    # 이 작업이 끝날 때까지 이 함수는 다음 줄로 넘어가지 못합니다.
    result = sync_blocking_task(2)

    # 작업이 끝난 뒤의 시간을 기록합니다.
    end_time = time.time()

    # 시작 시간과 종료 시간의 차이를 응답에 추가합니다.
    # 거의 2초 정도가 나와야 정상입니다.
    result["duration"] = f"{end_time - start_time:.2f}s (includes sync sleep)"

    return result


# 이 API의 핵심은 time.sleep()이 실행 흐름을 막는다는 점입니다.
# 사용자는 단순히 2초 기다리는 것으로 보이지만, 서버 입장에서는 그 시간 동안 현재 작업이 붙잡혀 있습니다.
# 그래서 동기 방식은 코드 흐름을 이해하기 쉽지만, 오래 기다리는 작업이 많아지면 여러 요청을 효율적으로 처리하기 어렵습니다.
# 특히 DB 조회, 외부 API 호출, 파일 처리처럼 기다리는 시간이 많은 작업에서는 비동기 방식이 더 유리할 수 있습니다.




####################################
# 비동기 방식 예제
####################################

# 지정한 초(duration)만큼 기다리지만, 실행 흐름 전체를 막지는 않는 비동기 함수입니다.
async def async_non_blocking_task(duration: int):
    print(f"Async task started, will await sleep for {duration} seconds...")

    # asyncio.sleep()은 Non-blocking 방식으로 기다리는 비동기 함수입니다.
    # await를 만나면 이 함수는 잠시 멈추지만, 서버 전체가 멈추는 것은 아닙니다.
    # 기다리는 동안 이벤트 루프는 다른 요청이나 다른 비동기 작업을 처리할 수 있습니다.
    await asyncio.sleep(duration)

    print(f"Async task finished after {duration} seconds.")

    return {"message": f"Asynchronous task complete after {duration}s"}


# 비동기 함수가 요청을 처리할 때 어떻게 기다리는지 확인하는 API입니다.
@app.get("/async-task")
async def run_async_task():

    # 시작 시간을 기록합니다.
    start_time = time.time()

    # async_non_blocking_task()는 비동기 함수이므로 await로 기다려야 합니다.
    # await는 "이 작업이 끝날 때까지 기다리되, 그동안 이벤트 루프가 다른 일을 해도 된다"는 뜻입니다.
    result = await async_non_blocking_task(2)   

    # 작업이 끝난 뒤의 시간을 기록합니다.
    end_time = time.time()

    # 시작 시간과 종료 시간의 차이를 응답에 추가합니다.
    # 이 요청 하나만 보면 약 2초가 걸리는 것은 동기 방식과 비슷합니다.
    result["duration"] = f"{end_time - start_time:.2f}s (includes async sleep)"

    return result


# 이 API 하나만 호출하면 /sync-task와 /async-task 모두 대략 2초 정도 걸립니다.
# 하지만 중요한 차이는 "기다리는 동안 서버가 다른 일을 할 수 있느냐"입니다.
# time.sleep()은 현재 흐름을 붙잡고 멈추지만, await asyncio.sleep()은 이벤트 루프에 제어권을 돌려줍니다.
# 그래서 비동기 방식은 동시에 많은 요청이 들어오는 웹 서버 환경에서 더 효율적으로 동작할 수 있습니다.


# 두 개의 비동기 작업을 거의 동시에 실행하는 예제입니다.
@app.get("/parallel-async")
async def run_parallel_async():
    
    # 시작 시간을 기록합니다.
    start_time = time.tiem()

    # async_non_blocking_task(1)과 async_non_blocking_task(2)는 아직 실제로 끝난 결과가 아닙니다.
    # 여기서는 "이런 비동기 작업을 실행할 준비가 된 코루틴"을 만든 것입니다.
    task1 = async_non_blocking_task(1)
    task2 = async_non_blocking_task(2)

    # asyncio.gather()는 여러 비동기 작업을 함께 실행하고, 모두 끝날 때까지 기다립니다.
    # task1은 1초, task2는 2초를 기다리지만 둘을 순서대로 기다리는 것이 아니라 거의 동시에 진행합니다.
    results = await asyncio.gather(task1, task2)

    # 두 작업이 모두 끝난 뒤의 시간을 기록합니다.
    end_time = time.time()

    # 동기 방식으로 순서대로 실행했다면 1초 + 2초라서 약 3초가 걸립니다.
    # 하지만 비동기 gather로 함께 실행하면 가장 오래 걸리는 작업인 2초에 가까운 시간이 걸립니다.
    # 이 예제가 보여주는 핵심은 비동기 작업은 "기다리는 시간"을 서로 겹쳐서 사용할 수 있다는 점입니다.
    return {
        "message": "Parallel async tasks complete!",
        "total_duration": f"{end_time - start_time:.2f}s",
        "results": results
    }
