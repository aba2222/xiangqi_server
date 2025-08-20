from typing import List
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketState

app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        "home_page.html", {"request": request, "message": "Hello, World!"}
    )


active_connections: List[WebSocket] = []


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            print(f"Message received for game {game_id}: {data}")
            for connection in active_connections:
                if connection != websocket:
                    await connection.send_json(data)

    except WebSocketDisconnect as e:
        print(f"Connection closed with code {e.code}")
        active_connections.remove(websocket)
    except Exception as e:
        # await websocket.send_text(f"Error occurred: {str(e)}")
        print(f"Error: {str(e)}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        if not websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1000, reason="Normal closure")
