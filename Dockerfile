FROM python:3.13-alpine
ENV PYTHONUNBUFFERED=1
RUN apk add g++ linux-headers libffi-dev rust cargo openssl-dev pkgconf make
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
RUN pip install supervisor whitenoise