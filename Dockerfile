# Отдельный сборочный образ
#FROM python:3.9-alpine as compile-image
FROM python:3.9-slim-buster as compile-image
#RUN \
# apk add --no-cache postgresql-libs && \
# apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
# apk add --no-cache build-base
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt
# Итоговый образ, в котором будет работать бот
#FROM python:3.9-alpine
FROM python:3.9-slim-buster
#RUN apk add --no-cache libpq
COPY --from=compile-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /usr/src/app/"${BOT_NAME:-tg_bot}"
COPY . /usr/src/app/"${BOT_NAME:-tg_bot}"
CMD ["python", "-m", "bot"]