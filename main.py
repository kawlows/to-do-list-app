from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from typing import List, Dict, Any
from pydantic import BaseModel
import json

app = FastAPI(title="Trello Clone - Single File")

# Jinja2 Templates
templates = Jinja2Templates(directory="templates")

# In-memory data store
data_store: Dict[str, Any] = {
    "boards": [],
    "current_board": None
}

# Pydantic models
class Card(BaseModel):
    id: str
    title: str
    description: str = ""
    color: str = "#0079bf"

class List(BaseModel):
    id: str
    title: str
    cards: List[Card] = []

# HTML Template (embedded)
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

        // Load boards
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

            // Initialize SortableJS drag & drop
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

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return HTMLResponse(HTML_TEMPLATE)

@app.get("/api/boards")
async def get_boards():
    return data_store["boards"]

@app.post("/api/boards")
async def create_board(board: Dict):
    board_id = f"board_{len(data_store['boards']) + 1}"
    new_board = {"id": board_id, "title": board.get("title", "Untitled"), "lists": []}
    data_store["boards"].append(new_board)
    return new_board

@app.get("/api/boards/{board_id}")
async def get_board(board_id: str):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            return board
    return {"error": "Board not found"}

@app.post("/api/boards/{board_id}/lists")
async def create_list(board_id: str, list_data: Dict):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            list_id = f"list_{len(board.get('lists', [])) + 1}"
            new_list = {"id": list_id, "title": list_data.get("title", "Untitled"), "cards": []}
            board["lists"].append(new_list)
            return new_list
    return {"error": "Board not found"}

@app.put("/api/boards/{board_id}/lists/{list_id}")
async def update_list(board_id: str, list_id: str, list_data: Dict):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            for list_item in board["lists"]:
                if list_item["id"] == list_id:
                    list_item["title"] = list_data.get("title")
                    return list_item
    return {"error": "List not found"}

@app.post("/api/boards/{board_id}/lists/{list_id}/cards")
async def create_card(board_id: str, list_id: str, card_data: Dict):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            for list_item in board["lists"]:
                if list_item["id"] == list_id:
                    card_id = f"card_{len(list_item.get('cards', [])) + 1}"
                    new_card = {
                        "id": card_id,
                        "title": card_data.get("title", "Untitled Card"),
                        "description": card_data.get("description", ""),
                        "color": "#0079bf"
                    }
                    list_item["cards"].append(new_card)
                    return new_card
    return {"error": "List not found"}

@app.delete("/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
async def delete_card(board_id: str, list_id: str, card_id: str):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            for list_item in board["lists"]:
                if list_item["id"] == list_id:
                    list_item["cards"] = [c for c in list_item["cards"] if c["id"] != card_id]
                    return {"message": "Card deleted"}
    return {"error": "Card not found"}

@app.post("/api/boards/{board_id}/move-card")
async def move_card(board_id: str, move_data: Dict):
    from_list_id = move_data.get("fromListId")
    to_list_id = move_data.get("toListId")
    card_id = move_data.get("cardId")
    
    for board in data_store["boards"]:
        if board["id"] == board_id:
            from_list = next((l for l in board["lists"] if l["id"] == from_list_id), None)
            to_list = next((l for l in board["lists"] if l["id"] == to_list_id), None)
            if from_list and to_list:
                card = next((c for c in from_list["cards"] if c["id"] == card_id), None)
                if card:
                    from_list["cards"] = [c for c in from_list["cards"] if c["id"] != card_id]
                    to_list["cards"].append(card)
                    return {"message": "Card moved"}
    return {"error": "Move failed"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
