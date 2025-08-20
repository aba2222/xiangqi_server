import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/12345"
    async with websockets.connect(uri) as websocket:
        # 发送消息
        await websocket.send(json.dumps({"message": "Hello, server!"}))
        
        # 接收响应
        response = await websocket.recv()
        print(f"Server response: {response}")

asyncio.run(test_websocket())
