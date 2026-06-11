from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
import asyncio


app = FastAPI()


#################################################
# WebSocket 텍스트 Echo 예제
#################################################

# WebSocket은 일반 HTTP 요청/응답과 다르게, 한 번 연결을 맺은 뒤 계속 데이터를 주고받을 수 있습니다.
# 일반 HTTP는 "요청 1번 -> 응답 1번 -> 연결 종료"에 가깝지만,
# WebSocket은 "연결 유지 -> 메시지 여러 번 주고받기" 방식입니다.

# 이 엔드포인트는 클라이언트가 보낸 텍스트를 그대로 다시 돌려주는 Echo 예제입니다.
# 예를 들어 클라이언트가 "hello"를 보내면 서버는 "Echo: hello"를 다시 보냅니다.
@app.websocket("/ws/echo")
async def websocket_echo_endpoint(websocket: WebSocket):

    # WebSocket 연결 요청을 수락합니다.
    # 클라이언트가 WebSocket 연결을 요청하면, 서버가 accept()를 호출해야 실제 통신이 시작됩니다.
    # accept()를 하지 않으면 클라이언트와 메시지를 주고받을 수 없습니다.
    await websocket.accept()

    # 연결된 클라이언트의 IP와 포트를 콘솔에 출력합니다.
    # 디버깅할 때 누가 연결했는지 확인하는 용도입니다.
    print(f"Client connected: {websocket.client.host}:{websocket.client.port}")

    try:
        # WebSocket 연결은 한 번 메시지를 받고 끝나는 구조가 아닙니다.
        # 클라이언트가 연결을 끊기 전까지 계속 메시지를 받을 수 있어야 하므로 while True를 사용합니다.
        while True:
            # 클라이언트가 보낸 텍스트 메시지를 기다립니다.
            # receive_text()는 클라이언트가 텍스트를 보낼 때까지 대기합니다.
            # 여기서 await를 사용하므로, 메시지를 기다리는 동안 서버 전체가 멈추지는 않습니다.
            data = await websocket.receive_text()

            # 클라이언트가 보낸 메시지를 서버 콘솔에 출력합니다.
            print(f"Message received from client: {data}")

            # 받은 메시지 앞에 "Echo: "를 붙여서 클라이언트에게 다시 보냅니다.
            # send_text()는 WebSocket 연결을 통해 텍스트 메시지를 전송합니다.
            await websocket.send_text(f"Echo: {data}")

            # 서버가 어떤 메시지를 다시 보냈는지 콘솔에 출력합니다.
            print(f"Message sent to client: Echo: {data}")
    
    except WebSocketDisconnect:
        # 클라이언트가 브라우저를 닫거나, 연결을 종료하면 WebSocketDisconnect가 발생합니다.
        # 정상적인 연결 종료 상황이므로 서버가 죽지 않게 여기서 처리합니다.
        print(f"Client disconnected: {websocket.client.host}:{websocket.client.port}")

    except Exception as e:
        # 예상하지 못한 에러가 발생했을 때 실행됩니다.
        # 예를 들어 메시지 처리 중 문제가 생기면 여기서 로그를 남깁니다.
        print(f"An error occurred: {e}")

        # 서버 내부 오류로 WebSocket 연결을 종료합니다.
        # WS_1011_INTERNAL_ERROR는 WebSocket에서 "서버 내부 오류"를 의미하는 종료 코드입니다.
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


# 이 Echo 예제의 전체 흐름은 다음과 같습니다.
# 클라이언트가 /ws/echo로 WebSocket 연결을 요청합니다.
# 서버가 accept()로 연결을 수락합니다.
# 이후 서버는 while True 안에서 클라이언트 메시지를 계속 기다립니다.
# 메시지를 받으면 "Echo: ..." 형태로 다시 클라이언트에게 보냅니다.
# 클라이언트가 연결을 끊으면 WebSocketDisconnect에서 종료 로그를 남기고 함수가 끝납니다.


##################################################
# JSON Echo 예제
##################################################

# 이 엔드포인트는 텍스트가 아니라 JSON 데이터를 주고받는 WebSocket 예제입니다.
# 클라이언트가 {"name": "secha"} 같은 JSON을 보내면,
# 서버는 {"received": {"name": "secha"}, "echoed": true} 같은 JSON을 다시 보냅니다.
@app.websocket("/ws/json_echo")
async def websocket_json_echo_endpoint(websocket: WebSocket):
    # JSON WebSocket 연결 요청을 수락합니다.
    await websocket.accept()

    # 연결된 클라이언트 정보를 출력합니다.
    print(f"JSON Client connected: {websocket.client}")

    try:
        # 클라이언트가 연결을 끊기 전까지 JSON 메시지를 계속 기다립니다.
        while True:
            # 클라이언트가 보낸 JSON 메시지를 기다립니다.
            # receive_json()은 받은 메시지를 Python dict 또는 list 형태로 변환해줍니다.
            # 단, 클라이언트가 올바른 JSON 형식이 아닌 데이터를 보내면 에러가 발생할 수 있습니다.
            data = await websocket.receive_json()

            # 받은 JSON 데이터를 콘솔에 출력합니다.
            print(f"JSON received: {data}")

            # 클라이언트에게 다시 보낼 JSON 응답 데이터를 만듭니다.
            # received에는 클라이언트가 보낸 원본 JSON을 넣고,
            # echoed에는 서버가 정상적으로 되돌려 보냈다는 표시를 넣습니다.
            response_data = {"received": data, "echoed": True}

            # JSON 응답을 WebSocket으로 클라이언트에게 보냅니다.
            # send_json()은 Python dict를 JSON 문자열로 변환해서 전송합니다.
            await websocket.send_json(response_data)

            # 서버가 보낸 JSON 응답을 콘솔에 출력합니다.
            print(f"JSON sent: {response_data}")
    
    except WebSocketDisconnect:
        # 클라이언트가 정상적으로 연결을 종료한 경우입니다.
        print(f"JSON Client disconnected: {websocket.client}")

    except Exception as e:
        # JSON 파싱 오류나 기타 예상하지 못한 문제가 발생하면 실행됩니다.
        print(f"JSON WebSocket Error: {e}")

        try:
            # 가능하면 클라이언트에게 에러 내용을 JSON으로 알려줍니다.
            # 단, 연결 상태가 이미 좋지 않을 수 있으므로 이 전송도 실패할 수 있습니다.
            await websocket.send_json({"error": str(e)})
        except:
            # 에러 응답 전송까지 실패해도 서버가 추가로 터지지 않게 무시합니다.
            pass

        # 서버 내부 오류 코드로 WebSocket 연결을 종료합니다.
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


# JSON Echo 예제의 전체 흐름은 텍스트 Echo와 거의 같습니다.
# 차이는 receive_text()/send_text() 대신 receive_json()/send_json()을 사용한다는 점입니다.
# 텍스트 WebSocket은 문자열 중심이고, JSON WebSocket은 dict/list 같은 구조화된 데이터를 주고받기 좋습니다.
# 실제 채팅, 알림, 실시간 상태 업데이트 같은 기능에서는 JSON 형태로 메시지 타입과 데이터를 함께 보내는 경우가 많습니다.
