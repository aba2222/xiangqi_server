from typing import Dict, List
import uuid
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketState

app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

games: Dict[str, Dict] = {}


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(
        "home_page.html", {"request": request, "message": "Hello, World!"}
    )

@app.get("/get_games")
async def get_games():
    return games

@app.post("/create_game")
async def create_game(game_code: str):
    game_id = str(uuid.uuid4())  # 生成唯一的 game_id
    games[game_id] = {"game_code": game_code, "players": []}  # 用于保存加入该对局的玩家
    return {"game_id": game_id}


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    if game_id not in games:
        await websocket.close(code=1008, reason="Game ID not found")
        return

    await websocket.accept()

    game_code = games[game_id]["game_code"]

    await websocket.send_json({"game_id": game_id, "game_code": game_code})

    games[game_id]["players"].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            print(f"Message received for game {game_id}: {data}")
            for connection in games[game_id]["players"]:
                if connection != websocket:
                    await connection.send_json(data)

    except WebSocketDisconnect as e:
        print(f"Connection closed with code {e.code}")
        games[game_id]["players"].remove(websocket)
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if websocket in games[game_id]["players"]:
            games[game_id]["players"].remove(websocket)

        if not websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1000, reason="Normal closure")
