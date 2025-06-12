# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from strawberry.asgi import GraphQL
from schema import schema
from client import clients

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://cnchatbnd-production.up.railway.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL setup
graphql_app = GraphQL(schema)
app.mount("/graphql", graphql_app)

@app.get("/")
def root():
    return {"message": "Chat backend is running!"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    username = websocket.query_params.get("username")
    if not username:
        await websocket.send_text("[ERROR] No username provided.")
        await websocket.close()
        return

    if username in clients:
        await websocket.send_text("[ERROR] Username already taken.")
        await websocket.close()
        return

    clients[username] = websocket
    await broadcast(f"[SERVER] {username} has joined the chat.", exclude=username)
    print(f"[CONNECTED] {username}")

    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith('@'):
                parts = data[1:].split(' ', 1)
                if len(parts) == 2:
                    recipient, msg = parts
                    await send_private_message(username, recipient, msg)
                else:
                    await websocket.send_text("[ERROR] Invalid private message format. Use @username message.")
            else:
                await broadcast(f"[{username}] {data}", exclude=username)

    except WebSocketDisconnect:
        print(f"[DISCONNECTED] {username}")
    finally:
        del clients[username]
        await broadcast(f"[SERVER] {username} has left the chat.")

async def broadcast(message: str, exclude: str = None):
    for user, ws in clients.items():
        if user != exclude:
            try:
                await ws.send_text(message)
            except:
                pass

async def send_private_message(sender: str, recipient: str, message: str):
    recipient_ws = clients.get(recipient)
    sender_ws = clients.get(sender)
    if recipient_ws:
        await recipient_ws.send_text(f"[PRIVATE] {sender}: {message}")
        await sender_ws.send_text(f"[TO {recipient}] {message}")
    else:
        await sender_ws.send_text(f"[ERROR] User {recipient} not found.")
