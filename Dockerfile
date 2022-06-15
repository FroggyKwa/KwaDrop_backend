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
CMD alembic upgrade head ; gunicorn -w 4 -b 0.0.0.0:${PORT} -k uvicorn.workers.UvicornWorker main:app
