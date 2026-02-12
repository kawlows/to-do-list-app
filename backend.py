from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import uvicorn

app = FastAPI(title="Trello Clone API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory data store
data_store: Dict[str, Any] = {"boards": []}

# ===== ALL API ROUTES =====
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
    raise HTTPException(status_code=404, detail="Board not found")

@app.post("/api/boards/{board_id}/lists")
async def create_list(board_id: str, list_data: Dict):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            list_id = f"list_{len(board.get('lists', [])) + 1}"
            new_list = {"id": list_id, "title": list_data.get("title", "Untitled"), "cards": []}
            board["lists"].append(new_list)
            return new_list
    raise HTTPException(status_code=404, detail="Board not found")

@app.put("/api/boards/{board_id}/lists/{list_id}")
async def update_list(board_id: str, list_id: str, list_data: Dict):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            for list_item in board["lists"]:
                if list_item["id"] == list_id:
                    list_item["title"] = list_data.get("title")
                    return list_item
    raise HTTPException(status_code=404, detail="List not found")

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
    raise HTTPException(status_code=404, detail="List not found")

@app.delete("/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
async def delete_card(board_id: str, list_id: str, card_id: str):
    for board in data_store["boards"]:
        if board["id"] == board_id:
            for list_item in board["lists"]:
                if list_item["id"] == list_id:
                    list_item["cards"] = [c for c in list_item["cards"] if c["id"] != card_id]
                    return {"message": "Card deleted"}
    raise HTTPException(status_code=404, detail="Card not found")

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
    raise HTTPException(status_code=404, detail="Move failed")

@app.get("/")
async def root():
    return {"message": "Trello Clone API - Visit /docs for API documentation"}

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
