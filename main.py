from fastapi import FastAPI
from fastapi.params import Body
from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import JSONResponse

from worker import create_task

from database.db import engine
from models import models, schemas
from routes import routes

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


@app.get("/")
async def home():
    return {"message": "Hello World"}


@app.post("/tasks", status_code=201)
def run_task(payload=Body(...)):
    task_type = payload["type"]
    task = create_task.delay(int(task_type))
    return JSONResponse({"task_id": task.id})

