import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load and index tasks
with open("tasks.json") as f:
    TASKS = json.load(f)
TASKS_BY_ID = {t["id"]: t for t in TASKS}

# Build reverse-dependency map
DEPENDENTS = {t["id"]: [] for t in TASKS}
for t in TASKS:
    for dep in t["dependencies"]:
        DEPENDENTS[dep].append(t["id"])

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/tasks")
async def get_tasks():
    return TASKS

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for ws in list(self.active):
            await ws.send_text(data)

manager = ConnectionManager()

class CookController:
    def __init__(self):
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._running = False
        self._tasks: dict[int, asyncio.Task] = {}
        self._completed: set[int] = set()

    async def start(self):
        if self._running:
            return
        self._running = True
        # schedule any with no deps
        for t in TASKS:
            if not t["dependencies"]:
                self._schedule(t["id"])

    async def pause(self):
        if self._pause_event.is_set():
            self._pause_event.clear()
            await manager.broadcast({"type": "paused"})
        else:
            self._pause_event.set()
            await manager.broadcast({"type": "resumed"})

    async def skip(self):
        # cancel all running tasks
        for task in self._tasks.values():
            task.cancel()
        # mark them completed
        for tid in list(self._tasks.keys()):
            await self._mark_complete(tid)
        await manager.broadcast({"type": "skipped_all"})

    def _schedule(self, task_id: int):
        if task_id in self._tasks or task_id in self._completed:
            return
        self._tasks[task_id] = asyncio.create_task(self._run_task(task_id))

    async def _run_task(self, task_id: int):
        t = TASKS_BY_ID[task_id]
        # notify start
        await manager.broadcast({
            "type": "start_task",
            "taskId": task_id,
            "name": t["name"],
            "duration": t["duration"],
            "assignedTo": t["assignedTo"],
            "startTime": datetime.utcnow().timestamp()
        })

        try:
            for elapsed in range(1, t["duration"] + 1):
                await self._pause_event.wait()
                await asyncio.sleep(1)
                await manager.broadcast({
                    "type": "progress",
                    "taskId": task_id,
                    "elapsed": elapsed,
                    "assignedTo": t["assignedTo"]
                })
        except asyncio.CancelledError:
            pass
        finally:
            await self._mark_complete(task_id)

    async def _mark_complete(self, task_id: int):
        if task_id in self._completed:
            return
        self._completed.add(task_id)
        self._tasks.pop(task_id, None)
        await manager.broadcast({
            "type": "complete_task",
            "taskId": task_id,
            "assignedTo": TASKS_BY_ID[task_id]["assignedTo"]
        })
        # schedule dependents if now ready
        for dep in DEPENDENTS[task_id]:
            prereqs = TASKS_BY_ID[dep]["dependencies"]
            if all(p in self._completed for p in prereqs):
                self._schedule(dep)
        if len(self._completed) == len(TASKS):
            await manager.broadcast({"type": "all_tasks_complete"})

controller = CookController()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()
            cmd = json.loads(msg).get("action")
            if cmd == "start": await controller.start()
            elif cmd == "pause": await controller.pause()
            elif cmd == "skip": await controller.skip()
    except WebSocketDisconnect:
        manager.disconnect(ws)
