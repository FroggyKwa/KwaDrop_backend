from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from authentication.routes import router as auth_router
from database.db import engine
from models import models
from routes.routes import router as main_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)

app.include_router(main_router)
app.include_router(auth_router)


@app.get("/")
async def home():
    return {"message": "Hello World"}
