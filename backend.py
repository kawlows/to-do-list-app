from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Dict
from sqlalchemy import create_engine, Column, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import uuid
import os

app = FastAPI(title="Trello Clone - SQLite")

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./trello.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class BoardDB(Base):
    __tablename__ = "boards"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True)
    lists = relationship("ListDB", back_populates="board", cascade="all, delete-orphan")

class ListDB(Base):
    __tablename__ = "lists"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True)
    board_id = Column(String, ForeignKey("boards.id"))
    board = relationship("BoardDB", back_populates="lists")
    cards = relationship("CardDB", back_populates="list_db", cascade="all, delete-orphan")

class CardDB(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True)
    description = Column(Text, default="")
    color = Column(String, default="#0079bf")
    list_id = Column(String, ForeignKey("lists.id"))
    list_db = relationship("ListDB", back_populates="cards")

Base.metadata.create_all(bind=engine)

# Serialization
def model_to_dict(obj):
    if obj is None: return None
    if isinstance(obj, list): return [model_to_dict(item) for item in obj]
    
    result = {}
    for c in obj.__table__.columns:
        value = getattr(obj, c.name)
        if isinstance(value, (str, int, float, bool, type(None))):
            result[c.name] = value
        else:
            result[c.name] = str(value)
    
    if isinstance(obj, BoardDB): result['lists'] = model_to_dict(obj.lists)
    elif isinstance(obj, ListDB): result['cards'] = model_to_dict(obj.cards)
    
    return result

# Routes
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html") as f:
        return HTMLResponse(f.read())

@app.get("/api/boards")
async def get_boards(db: Session = Depends(get_db)):
    return [model_to_dict(b) for b in db.query(BoardDB).all()]

@app.post("/api/boards")
async def create_board(data: Dict, db: Session = Depends(get_db)):
    board = BoardDB(title=data.get("title", "Untitled"))
    db.add(board)
    db.commit()
    db.refresh(board)
    return model_to_dict(board)

@app.get("/api/boards/{board_id}")
async def get_board(board_id: str, db: Session = Depends(get_db)):
    board = db.query(BoardDB).filter(BoardDB.id == board_id).first()
    if not board: raise HTTPException(404, "Board not found")
    return model_to_dict(board)

@app.post("/api/boards/{board_id}/lists")
async def create_list(board_id: str, data: Dict, db: Session = Depends(get_db)):
    board = db.query(BoardDB).filter(BoardDB.id == board_id).first()
    if not board: raise HTTPException(404, "Board not found")
    lst = ListDB(title=data.get("title", "New List"), board=board)
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return model_to_dict(lst)

@app.put("/api/boards/{board_id}/lists/{list_id}")
async def update_list(board_id: str, list_id: str, data: Dict, db: Session = Depends(get_db)):
    lst = db.query(ListDB).filter(ListDB.id == list_id, ListDB.board_id == board_id).first()
    if not lst: raise HTTPException(404, "List not found")
    lst.title = data.get("title")
    db.commit()
    db.refresh(lst)
    return model_to_dict(lst)

@app.post("/api/boards/{board_id}/lists/{list_id}/cards")
async def create_card(board_id: str, list_id: str, data: Dict, db: Session = Depends(get_db)):
    lst = db.query(ListDB).filter(ListDB.id == list_id, ListDB.board_id == board_id).first()
    if not lst: raise HTTPException(404, "List not found")
    card = CardDB(title=data.get("title", "New Card"), list_id=lst.id)
    db.add(card)
    db.commit()
    db.refresh(card)
    return model_to_dict(card)

@app.delete("/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
async def delete_card(board_id: str, list_id: str, card_id: str, db: Session = Depends(get_db)):
    card = db.query(CardDB).filter(CardDB.id == card_id, CardDB.list_id == list_id).first()
    if not card: raise HTTPException(404, "Card not found")
    db.delete(card)
    db.commit()
    return {"message": "Deleted"}

@app.post("/api/boards/{board_id}/move-card")
async def move_card(board_id: str, data: Dict, db: Session = Depends(get_db)):
    card = db.query(CardDB).filter(CardDB.id == data["cardId"]).first()
    if card: 
        card.list_id = data["toListId"]
        db.commit()
        return {"message": "Moved"}
    raise HTTPException(400, "Move failed")

if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
