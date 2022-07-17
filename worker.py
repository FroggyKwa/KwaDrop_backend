import os
import time

from celery import Celery
from dotenv import load_dotenv

import models.models
from database.db import get_db
from helpers import delete_images_not_in_db

celery = Celery(__name__)
load_dotenv()
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")
# celery.conf.beat_schedule = {
#     "clean images every 30 minutes":{
#         'task': 'clean_images',
#         'schedule': 1,
#     }
# }

db = get_db()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls clean_images() every 30 minutes.
    sender.add_periodic_task(1800.0, clean_images, name='clean images every 30 minutes')
    sender.add_periodic_task(10.0, hello_world, name='print hello world')


@celery.task(name="create_task")
def create_task(task_type):
    pass
    return True


@celery.task(name="clean_images")
def clean_images():
    delete_images_not_in_db()
    return True


@celery.task(name="hello_world")
def hello_world():
    print("Hello world!")
    return True
