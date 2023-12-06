import asyncio
import base64
import json
import logging
import time

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models.constants import gcp_icons

app = FastAPI()

logger = logging.getLogger('uvicorn.app')


templates = Jinja2Templates(directory="templates")

users = {}
answers = {}
begin_time = 0.0


# https://fastapi.tiangolo.com/advanced/websockets/
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

# static folder
# https://fastapi.tiangolo.com/tutorial/static-files/
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def lobby(request: Request):
    return templates.TemplateResponse(
        "lobby.html",
        {
            "request": request,
            "hostname": ""
        }
    )

# ゲームのステータスを管理する global 変数
status = {
    "isKarutaStarted": False,
    "isHinting": False,
    "isHintEnded": False
}


@app.get("/game/{base64d_user_id}", response_class=HTMLResponse)
async def game(request: Request, base64d_user_id: str):
    user_id = base64.b64decode(base64d_user_id).decode()
    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "base64d_user_id": base64d_user_id,
            "user_id": user_id,
            "icons": gcp_icons,
        }
    )


def is_parent(client_id: str):
    return users[client_id] == 10


def get_description(name: str):
    for icon in gcp_icons:
        if icon["name"] == name:
            return icon["desc"]


def get_current_status():
    for client_id in users.keys():
        if users[client_id] == 10:
            status["isKarutaStarted"] = True
            break

    return status


def create_message(message_type: str, value, user_name="system"):
    return json.dumps(
        {
            "messageType": message_type,
            "user": user_name,
            "value": value
        }
    )


def game_init():
    global status
    status = {
        "isKarutaStarted": False,
        "isHinting": False,
        "isHintEnded": False
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    global users
    user_name = base64.b64decode(client_id).decode()
    if client_id not in users:
        users[client_id] = 1
    await manager.send_personal_message(
        create_message(
            "UI",
            get_current_status(),
        ),
        websocket,
    )
    try:
        while True:
            data = await websocket.receive_text()
            global answers
            global status
            global begin_time
            logger.info(f"Get messages: {str(data)} from {client_id}, {user_name}")
            logger.info(f"users: {str(users)}")
            logger.info(f"status: {str(status)}")
            # かるたゲームを始める
            user_name = base64.b64decode(client_id).decode()
            # protocol の解析
            if data.startswith("[Choose]"):
                chosen = data.split(',')[1].split('-')[1]
                if status["isHinting"] and not status["isHintEnded"]:
                    if not is_parent(client_id):
                        if user_name not in answers:
                            # 0秒未満は0秒に丸める
                            answered_time = round(time.time() - begin_time, 3)
                            if answered_time < 0:
                                answered_time = 0
                            answers[user_name] = {
                                "chosen": chosen,
                                "answeredTime": answered_time
                            }
                            await manager.broadcast(
                                create_message(
                                    "SYSTEM_GAME",
                                    f"{user_name} が {chosen} を選択！"
                                )
                            )
                        else:
                            # 選択済みなのでスルー
                            pass
                elif status["isKarutaStarted"]:
                    status["isHinting"] = True
                    answers = {}
                    if is_parent(client_id):
                        # is_hinting
                        chosen = data.split(',')[1].split('-')[1]
                        desc = get_description(chosen)
                        await manager.send_personal_message(
                            create_message(
                                "SYSTEM",
                                f"{chosen} を選択。問題を送信します。"
                            ),
                            websocket
                        )
                        await manager.broadcast(
                            create_message(
                                "SYSTEM_GAME",
                                f"画面上部に表示されるヒントに該当する Google Cloud 製品を選択してください！"
                            )
                        )
                        begin_time = time.time()
                        await manager.broadcast(
                            create_message("HINT_START", {})
                        )
                        await asyncio.sleep(1)
                        for word in desc.split(" "):
                            await manager.broadcast(
                                create_message(
                                    "HINT",
                                    word,
                                )
                            )
                            await asyncio.sleep(1)
                        status["isHintEnded"] = True
                        await manager.broadcast(
                            create_message("HINT_END", {})
                        )
                        await asyncio.sleep(1)
                        # 正解を broadcast
                        await manager.broadcast(
                            create_message(
                                "SYSTEM_GAME",
                                f"正解は: [{chosen}] でした。"
                            )
                        )
                        # 回答している人がいたら正答判定を送る
                        if answers:
                            for user_name in answers.keys():
                                if answers[user_name]["chosen"] == chosen:
                                    uat = answers[user_name]['answeredTime']
                                    await manager.broadcast(
                                        create_message(
                                            "SYSTEM_GAME",
                                            f"{user_name} さん、正解です！ タイム[{uat}] sec"
                                        )
                                    )
                        await asyncio.sleep(1)
                        await manager.broadcast(
                            create_message(
                                "SYSTEM",
                                "次のゲーム開始までお待ち下さい。"
                            )
                        )
                        status["isHintEnded"] = False
                        status["isHinting"] = False
                    else:
                        # 何もなし
                        pass
            elif data == "[StartGame]":
                # 親を決める
                users[client_id] = 10
                status["isKarutaStarted"] = True
                await manager.send_personal_message(
                    create_message(
                        "SYSTEM",
                        "かるたゲームをはじめます。あなたがゲームマスターです。Google Cloud のいずれかのアイコンを選択してください。",
                    ),
                    websocket
                )
                await manager.broadcast(
                    create_message(
                        "START_GAME",
                        "",
                    )
                )
                await manager.broadcast(
                    create_message(
                        "SYSTEM",
                        f"{user_name} さんがかるたゲームを始めました！開始までもう少々お待ち下さい",
                    )
                )
            elif data == "[EndGame]":
                users[client_id] = 10
                status["isKarutaStarted"] = False
                await manager.broadcast(
                    create_message(
                        "END_GAME",
                        "",
                    )
                )
                await manager.broadcast(
                    create_message(
                        "SYSTEM",
                        "ゲームを終了しました。",
                    )
                )
            else:
                await manager.send_personal_message(
                    create_message(
                        "SYSTEM",
                        f"You wrote: {data}",
                    ),
                    websocket
                )
                await manager.broadcast(
                    create_message(
                        "MESSAGE",
                        data,
                        user_name=user_name
                    )
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if users.get(client_id) == 10:
            game_init()
        users.pop(client_id, None)
        await manager.broadcast(
            create_message(
                "SYSTEM",
                f"Client #{client_id} left the chat."
            )
        )
