from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from uuid import uuid4

DATABASE_URL = "sqlite:///./game_data.db"

Base = declarative_base()

# 创建数据库引擎
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 创建表结构
class Game(Base):
    __tablename__ = "games"

    id = Column(String, primary_key=True, index=True)
    game_code = Column(String, index=True)
    players = relationship("Player", back_populates="game")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    websocket_id = Column(String, index=True)
    game_id = Column(String, ForeignKey("games.id"))

    game = relationship("Game", back_populates="players")


# 创建所有表
Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(
        "home_page.html", {"request": request, "message": "Hello, World!"}
    )


# @app.get("/get_games")
# async def get_games():
# return games


@app.post("/create_game")
async def create_game(game_code: str, db: Session = Depends(get_db)):
    game_id = str(uuid4())  # 生成唯一的 game_id

    db_game = Game(id=game_id, game_code=game_code)
    db.add(db_game)
    db.commit()
    db.refresh(db_game)  # 获取数据库中的新记录

    return {"game_id": game_id}

    game_id = str(uuid.uuid4())  # 生成唯一的 game_id
    games[game_id] = {"game_code": game_code, "players": []}  # 用于保存加入该对局的玩家
    return {"game_id": game_id}


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket, game_id: str, db: Session = Depends(get_db)
):
    if not db.query(Game).filter(Game.id == game_id).first():
        await websocket.close(code=1008, reason="Game ID not found")
        return

    await websocket.accept()

    game_code = db.query(Game).filter(Game.id == game_id).first().game_code

    await websocket.send_json({"game_id": game_id, "game_code": game_code})

    # 在数据库中为玩家创建记录
    db_player = Player(websocket_id=str(websocket.client), game_id=game_id)
    db.add(db_player)
    db.commit()

    try:
        while True:
            data = await websocket.receive_json()
            print(f"Message received for game {game_id}: {data}")
            for player in db.query(Player).filter(Player.game_id == game_id).all():
                if player.websocket_id != str(websocket.client):
                    await websocket.send_json(data)

    except WebSocketDisconnect as e:
        print(f"Connection closed with code {e.code}")
        db.query(Player).filter(Player.websocket_id == str(websocket.client)).delete()
        db.commit()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if (
            db.query(Player)
            .filter(Player.websocket_id == str(websocket.client))
            .first()
        ):
            db.query(Player).filter(
                Player.websocket_id == str(websocket.client)
            ).delete()
            db.commit()
            await websocket.close(code=1000, reason="Normal closure")
