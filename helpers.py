import os
import datetime

import aiofiles
from fastapi import UploadFile, HTTPException

import models.models
from database.db import SessionLocal


async def save_file(file: UploadFile, out_path: str, max_size=15):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Загружать можно только картинки")

    size = 1024
    async with aiofiles.open(out_path, "wb") as out_file:
        content = await file.read(1024 * 1024)
        while content:
            await out_file.write(content)
            content = await file.read(1024 * 1024)
            size += 1024

            if max_size:
                if size / 1024 > max_size:
                    os.unlink(out_path)
                    raise HTTPException(status_code=400, detail="File exceeds max size")


def get_image_links():
    links = [f for f in os.listdir(os.getcwd() + '/images') if f.split('.')[-1] == 'jpg']
    return links


def delete_images_not_in_db():
    db = SessionLocal()
    db_links = [i.avatar.split('images/')[1] for i in db.query(models.models.User).all() if i.avatar is not None]
    links = get_image_links()
    for i in links:
        if i not in db_links:
            if datetime.datetime.now().timestamp() - os.path.getmtime(os.getcwd() + '/images/' + i) > 1800:
                os.remove(os.getcwd() + '/images/' + i)
    return
