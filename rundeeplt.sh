#!/bin/bash

# Redis 서버 실행
redis-server &

# Celery 작업자 실행
celery -A app.celery worker --loglevel=info --autoscale=1,1 &

# Flask 애플리케이션 실행
authbind --deep python app.py &
