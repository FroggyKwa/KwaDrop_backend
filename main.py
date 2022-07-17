from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from fastapi.params import Body
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from worker import create_task

from database.db import engine
from models import models
from routes import routes, room_routes, song_routes, user_routes

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="KwaDrop Backend API")

origins = [
    "http://localhost:8021",
    "https://localhost:8021",
    "http://localhost:8080",
    "https://localhost:8080",
    "http://app",
    "https://app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["set-cookie", "Set-Cookie"],
)

app.include_router(routes.router)
app.include_router(user_routes.router)
app.include_router(room_routes.router)
app.include_router(song_routes.router)


@app.get("/")
async def home():
    return {"message": "Hello World"}


@app.post("/tasks", status_code=201)
def run_task(payload=Body(...)):
    task_types = [0]
    task_type = payload["type"]
    if task_type not in task_types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application do not support tasks with type{task_type}.",
        )
    task = create_task.delay(int(task_type))
    return JSONResponse({"task_id": task.id})


@app.get("/tasks/{task_id}")
def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    return JSONResponse(result)
