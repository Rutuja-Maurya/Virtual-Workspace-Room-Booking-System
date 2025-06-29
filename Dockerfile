# Dockerfile for Django + PostgreSQL
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /code/

CMD ["gunicorn", "virtual_workspace.wsgi:application", "--chdir", "/code/virtual_workspace", "--bind", "0.0.0.0:8000"]
