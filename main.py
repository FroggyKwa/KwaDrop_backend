from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.db import engine
from models import models, schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)


@app.get("/")
async def home():
    return {"message": "Hello World"}
