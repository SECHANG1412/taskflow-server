import time
import asyncio
from fastapi import FastAPI

app = FastAPI()


###############################################################
# 문제 상황: async def 안에서 블로킹 함수를 직접 호출하는 경우
###############################################################

# async def로 만든 API라도 내부에서 time.sleep()을 직접 실행하면 문제가 됩니다.
# time.sleep()은 Blocking 함수라서, 실행되는 동안 이벤트 루프를 붙잡고 멈춥니다.
# 이벤트 루프가 멈추면 다른 비동기 요청도 제때 처리되지 못합니다.
@app.get("/blocking-sleep")
async def route_blocking_sleep():
    print("??Blocking: Received request. Starting time.sleep(5)...")

    # 이 줄이 핵심 문제입니다.
    # time.sleep(5)는 현재 실행 흐름을 5초 동안 완전히 멈춥니다.
    # async def 안에 있다고 해서 time.sleep()이 자동으로 비동기처럼 바뀌지 않습니다.
    # 이 5초 동안 이벤트 루프는 다른 작업으로 넘어가지 못하고 기다리게 됩니다.
    time.sleep(5)

    print("??Blocking: Woke up after 5 seconds.")
    return {"message": "Blocking sleep finished. If other requests were sent, they likely waited."}


# 이 API는 "async def 안에서도 블로킹 코드를 쓰면 위험하다"는 것을 보여주는 예제입니다.
# 겉으로는 비동기 함수처럼 보이지만, 내부의 time.sleep() 때문에 실제로는 이벤트 루프를 막습니다.
# 예를 들어 /blocking-sleep 요청을 보낸 직후 /ping 요청을 보내면,
# /ping도 바로 응답하지 못하고 time.sleep(5)가 끝날 때까지 기다릴 수 있습니다.
# 그래서 FastAPI에서 async def를 사용할 때는 내부에 블로킹 함수가 들어가지 않도록 조심해야 합니다.




################################################
# 해결책: asyncio.to_thread 사용
################################################

# 어쩔 수 없이 블로킹 함수를 써야 할 때는 asyncio.to_thread()로 별도 스레드에 맡길 수 있습니다.
# time.sleep() 자체는 여전히 블로킹 함수지만, 이벤트 루프에서 직접 실행하지 않게 만드는 방식입니다.
@app.get("/non-blocking-sleep")
async def route_non_blocking_sleep():
    print("??Non-blocking: Received request. Starting await asyncio.to_thread(time.sleep, 5)...")

    # asyncio.to_thread(time.sleep, 5)는 time.sleep(5)를 별도 스레드에서 실행하게 합니다.
    # await는 그 작업이 끝날 때까지 결과를 기다립니다.
    # 하지만 기다리는 동안 이벤트 루프는 막히지 않기 때문에 다른 요청을 처리할 수 있습니다.
    # 즉, 블로킹 작업을 이벤트 루프 밖으로 빼내는 안전장치라고 보면 됩니다.
    await asyncio.to_thread(time.sleep, 5)

    print("??Non-blocking: Background sleep finished after 5 seconds.")
    return {"message": "Non-blocking sleep finished via thread. Other requests could be processed."}


# 이 API는 비동기 라이브러리를 사용할 수 없을 때 쓰는 현실적인 대안입니다.
# 어떤 라이브러리가 동기 방식만 지원한다면, async def 안에서 바로 호출하면 이벤트 루프가 막힙니다.
# 그럴 때 asyncio.to_thread()로 감싸면 그 블로킹 작업을 별도 스레드에서 실행할 수 있습니다.
# 다만 이것이 "완전한 비동기 코드"로 바뀐다는 뜻은 아닙니다.
# 가장 좋은 방법은 여전히 처음부터 비동기 라이브러리를 사용하는 것입니다.




################################################
# 가장 좋은 방식: 네이티브 비동기 함수 사용
################################################

# asyncio.sleep()은 처음부터 비동기 방식으로 만들어진 sleep 함수입니다.
# 단순히 기다리는 예제에서는 time.sleep()보다 asyncio.sleep()이 async def와 더 잘 맞습니다.
@app.get("/asyncio-sleep")
async def route_asyncio_sleep():
    print("?? Asyncio: Received request. Starting await asyncio.sleep(5)...")

    # asyncio.sleep(5)는 5초 동안 기다리지만 이벤트 루프를 막지 않습니다.
    # await를 만나면 현재 함수는 잠시 멈추고, 이벤트 루프는 다른 요청을 처리할 수 있습니다.
    # 5초가 지나면 이벤트 루프가 다시 이 함수로 돌아와 다음 줄부터 실행합니다.
    await asyncio.sleep(5)

    print("?? Asyncio: Woke up after 5 seconds.")
    return {"message": "asyncio.sleep finished. Event loop was fully available."}


# 이 API는 네이티브 비동기 함수가 가장 깔끔한 해결책이라는 것을 보여줍니다.
# time.sleep()을 to_thread로 감싸는 것은 어쩔 수 없을 때의 대안입니다.
# 하지만 asyncio.sleep(), 비동기 DB 드라이버, 비동기 HTTP 클라이언트처럼
# 처음부터 async/await를 지원하는 라이브러리를 쓰면 이벤트 루프와 가장 자연스럽게 동작합니다.


# 다른 요청이 블로킹되는지 확인하기 위한 간단한 테스트용 엔드포인트입니다.
@app.get("/ping")
async def ping():
    print("?룗 Ping request received!")
    return {"message": "pong"}


# 테스트할 때는 /blocking-sleep, /non-blocking-sleep, /asyncio-sleep 중 하나를 먼저 호출하고,
# 바로 이어서 /ping을 호출해보면 차이를 이해하기 쉽습니다.
#
# /blocking-sleep은 time.sleep() 때문에 이벤트 루프를 막을 수 있습니다.
# 그래서 /ping 응답도 늦어질 수 있습니다.
#
# /non-blocking-sleep은 time.sleep()을 별도 스레드로 보냅니다.
# 그래서 sleep이 도는 동안에도 /ping 요청을 처리할 여지가 생깁니다.
#
# /asyncio-sleep은 처음부터 비동기 sleep을 사용합니다.
# 이벤트 루프를 막지 않으므로 비동기 FastAPI 코드에 가장 잘 맞는 방식입니다.
