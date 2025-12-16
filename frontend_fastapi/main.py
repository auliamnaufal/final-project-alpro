from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio, websockets, requests

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/screenshots", StaticFiles(directory="../backend_fastapi/screenshots"), name="screenshots")

templates = Jinja2Templates(directory="templates")

BACKEND_URL = "ws://127.0.0.1:8000/yolo"
BACKEND_API = "http://127.0.0.1:8000/api"

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin")
def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.websocket("/frontend")
async def proxy(client_ws: WebSocket):
    await client_ws.accept()

    async with websockets.connect(BACKEND_URL) as backend_ws:

        async def client_to_backend():
            while True:
                msg = await client_ws.receive_text()
                await backend_ws.send(msg)

        async def backend_to_client():
            while True:
                res = await backend_ws.recv()
                await client_ws.send_text(res)

        await asyncio.gather(client_to_backend(), backend_to_client())
@app.get("/api/latest")
def latest():
    res = requests.get(f"{BACKEND_API}/latest")
    return res.json()