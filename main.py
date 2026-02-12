from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn
from typing import List, Dict
from sqlalchemy import create_engine, Column, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import uuid

app = FastAPI(title="Trello Clone - SQLite")

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./trello.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# SQLAlchemy Models
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

# Create tables
Base.metadata.create_all(bind=engine)

# FIXED: Proper serialization function
def model_to_dict(obj):
    if obj is None:
        return None
    
    if isinstance(obj, list):
        return [model_to_dict(item) for item in obj]
    
    result = {}
    for c in obj.__table__.columns:
        value = getattr(obj, c.name)
        if isinstance(value, (str, int, float, bool, type(None))):
            result[c.name] = value
        elif hasattr(value, '__table__'):  # Another SQLAlchemy model
            result[c.name] = model_to_dict(value)
        else:
            result[c.name] = str(value)  # Convert other types to string
    
    # Manually add relationships
    if isinstance(obj, BoardDB):
        result['lists'] = model_to_dict(obj.lists)
    elif isinstance(obj, ListDB):
        result['cards'] = model_to_dict(obj.cards)
    
    return result

# Your existing HTML_TEMPLATE (unchanged - keeping it short here for brevity)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>awat awat sa trello</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
    <style>
        .list-container { min-height: 50vh; }
        .card { transition: all 0.3s ease; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .list { background: #ebecf0; border-radius: 8px; }
    </style>
</head>
<body class="bg-gray-100 p-8">
    <div class="max-w-7xl mx-auto">
        <h1 class="text-4xl font-bold mb-8 text-gray-800">trello wannabe</h1>
        
        <!-- Board Controls -->
        <div class="mb-8 flex gap-4">
            <input id="boardTitle" class="p-2 border rounded-lg w-64" placeholder="Board Title">
            <button onclick="createBoard()" class="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600">New Board</button>
        </div>

        <!-- Boards Grid -->
        <div id="boardsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12"></div>

        <!-- Current Board -->
        <div id="currentBoard" class="hidden">
            <div class="flex justify-between items-center mb-6">
                <h2 id="boardName" class="text-3xl font-bold"></h2>
                <div class="flex gap-2">
                    <input id="newListName" class="p-2 border rounded-lg w-48" placeholder="New List">
                    <button onclick="addList()" class="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600">Add List</button>
                </div>
            </div>
            <div id="listsContainer" class="flex gap-4 overflow-x-auto pb-4"></div>
        </div>
    </div>

    <script>
        let currentBoardId = null;
        let boardData = {};

        fetch('/api/boards').then(r => r.json()).then(data => {
            displayBoards(data);
        });

        function displayBoards(boards) {
            const grid = document.getElementById('boardsGrid');
            grid.innerHTML = boards.map(b => `
                <div class="bg-white p-6 rounded-xl shadow-lg cursor-pointer hover:shadow-xl transition-all" onclick="loadBoard('${b.id}')">
                    <h3 class="text-xl font-semibold mb-2">${b.title}</h3>
                    <p class="text-gray-500">${b.lists?.length || 0} lists</p>
                </div>
            `).join('');
        }

        function createBoard() {
            const title = document.getElementById('boardTitle').value || 'Untitled Board';
            fetch('/api/boards', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title})
            }).then(r => r.json()).then(data => {
                displayBoards([data]);
                document.getElementById('boardTitle').value = '';
            });
        }

        function loadBoard(boardId) {
            currentBoardId = boardId;
            fetch(`/api/boards/${boardId}`).then(r => r.json()).then(data => {
                boardData = data;
                document.getElementById('boardName').textContent = data.title;
                document.getElementById('currentBoard').classList.remove('hidden');
                document.getElementById('boardsGrid').classList.add('hidden');
                renderLists(data.lists);
            });
        }

        function renderLists(lists) {
            const container = document.getElementById('listsContainer');
            container.innerHTML = lists.map(list => `
                <div class="list bg-gray-200 min-w-[300px] p-4 rounded-xl list-container" data-list-id="${list.id}">
                    <div class="flex justify-between mb-4">
                        <input class="w-full p-2 bg-transparent border-b border-gray-400 text-lg font-semibold" value="${list.title}" onchange="updateList('${list.id}', this.value)">
                    </div>
                    <div class="space-y-3 min-h-[200px]">
                        ${list.cards.map(card => `
                            <div class="card bg-white p-4 rounded-lg shadow-md relative group" data-card-id="${card.id}">
                                <div class="font-medium mb-1">${card.title}</div>
                                ${card.description ? `<p class="text-sm text-gray-600 mb-2">${card.description}</p>` : ''}
                                <div class="flex gap-2 absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-all">
                                    <button onclick="editCard('${list.id}', '${card.id}')" class="text-xs text-blue-500 hover:text-blue-700">Edit</button>
                                    <button onclick="deleteCard('${list.id}', '${card.id}')" class="text-xs text-red-500 hover:text-red-700">Delete</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="mt-4">
                        <input id="card-${list.id}" class="w-full p-2 border rounded-lg text-sm" placeholder="Add a card">
                        <button onclick="addCard('${list.id}')" class="w-full mt-2 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 text-sm">Add Card</button>
                    </div>
                </div>
            `).join('');

            lists.forEach((list, index) => {
                new Sortable(document.querySelector(`[data-list-id="${list.id}"] .space-y-3`), {
                    group: 'kanban',
                    animation: 200,
                    onEnd: function(evt) {
                        const cardId = evt.item.dataset.cardId;
                        const newListId = evt.to.closest('[data-list-id]').dataset.listId;
                        moveCard(currentBoardId, list.id, newListId, cardId);
                    }
                });
            });
        }

        function addList() {
            const name = document.getElementById('newListName').value;
            if (!name || !currentBoardId) return;
            fetch(`/api/boards/${currentBoardId}/lists`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title: name})
            }).then(r => r.json()).then(() => {
                loadBoard(currentBoardId);
                document.getElementById('newListName').value = '';
            });
        }

        function addCard(listId) {
            const title = document.getElementById(`card-${listId}`).value;
            if (!title || !currentBoardId) return;
            fetch(`/api/boards/${currentBoardId}/lists/${listId}/cards`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title})
            }).then(() => {
                loadBoard(currentBoardId);
                document.getElementById(`card-${listId}`).value = '';
            });
        }

        function updateList(listId, title) {
            fetch(`/api/boards/${currentBoardId}/lists/${listId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title})
            });
        }

        function deleteCard(listId, cardId) {
            fetch(`/api/boards/${currentBoardId}/lists/${listId}/cards/${cardId}`, {
                method: 'DELETE'
            }).then(() => loadBoard(currentBoardId));
        }

        function moveCard(boardId, fromListId, toListId, cardId) {
            fetch(`/api/boards/${boardId}/move-card`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({fromListId, toListId, cardId})
            });
        }
    </script>
</body>
</html>
"""

# API Routes - NOW FIXED
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return HTMLResponse(HTML_TEMPLATE)

@app.get("/api/boards")
async def get_boards(db: Session = Depends(get_db)):
    boards = db.query(BoardDB).all()
    return [model_to_dict(board) for board in boards]

@app.post("/api/boards")
async def create_board(board_data: Dict, db: Session = Depends(get_db)):
    new_board = BoardDB(title=board_data.get("title", "Untitled Board"))
    db.add(new_board)
    db.commit()
    db.refresh(new_board)
    return model_to_dict(new_board)

@app.get("/api/boards/{board_id}")
async def get_board(board_id: str, db: Session = Depends(get_db)):
    board = db.query(BoardDB).filter(BoardDB.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return model_to_dict(board)

@app.post("/api/boards/{board_id}/lists")
async def create_list(board_id: str, list_data: Dict, db: Session = Depends(get_db)):
    board = db.query(BoardDB).filter(BoardDB.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    new_list = ListDB(title=list_data.get("title", "New List"), board=board)
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    return model_to_dict(new_list)

@app.put("/api/boards/{board_id}/lists/{list_id}")
async def update_list(board_id: str, list_id: str, list_data: Dict, db: Session = Depends(get_db)):
    list_item = db.query(ListDB).filter(ListDB.id == list_id, ListDB.board_id == board_id).first()
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    
    list_item.title = list_data.get("title")
    db.commit()
    db.refresh(list_item)
    return model_to_dict(list_item)

@app.post("/api/boards/{board_id}/lists/{list_id}/cards")
async def create_card(board_id: str, list_id: str, card_data: Dict, db: Session = Depends(get_db)):
    list_item = db.query(ListDB).filter(ListDB.id == list_id, ListDB.board_id == board_id).first()
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    
    new_card = CardDB(
        title=card_data.get("title", "New Card"),
        description=card_data.get("description", ""),
        color="#0079bf",
        list_id=list_item.id
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return model_to_dict(new_card)

@app.delete("/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
async def delete_card(board_id: str, list_id: str, card_id: str, db: Session = Depends(get_db)):
    card = db.query(CardDB).filter(CardDB.id == card_id, CardDB.list_id == list_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db.delete(card)
    db.commit()
    return {"message": "Card deleted"}

@app.post("/api/boards/{board_id}/move-card")
async def move_card(board_id: str, move_data: Dict, db: Session = Depends(get_db)):
    from_list_id = move_data.get("fromListId")
    to_list_id = move_data.get("toListId")
    card_id = move_data.get("cardId")
    
    card = db.query(CardDB).filter(CardDB.id == card_id).first()
    if card:
        card.list_id = to_list_id
        db.commit()
        return {"message": "Card moved"}
    
    raise HTTPException(status_code=400, detail="Move failed")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
