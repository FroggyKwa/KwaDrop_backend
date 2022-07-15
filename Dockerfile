FROM python:3.9.5-alpine

ARG NAME
ARG PORT

WORKDIR /usr/src/${NAME}_backend

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip3 install --upgrade pip
RUN apk --update add gcc make g++ zlib-dev
COPY ./requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt


COPY . "/usr/src/${NAME}_backend"
CMD alembic revision --autogenerate -m "init" ; alembic upgrade head ; gunicorn -w 1 -b 0.0.0.0:${PORT} -k uvicorn.workers.UvicornWorker main:app ssl_keyfile "/etc/letsencrypt/live/kwa-drop.ru/key.pem" ssl_certfile "/etc/letsencrypt/live/kwa-drop.ru/chain.pem"
