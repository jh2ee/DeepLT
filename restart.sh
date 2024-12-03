#!/bin/bash

# 종료할 프로세스들
pkill -f redis-server
pkill -f 'celery -A app.celery worker'
pkill -f 'authbind --deep python app.py'

# 잠시 대기 (선택사항)
sleep 2

# Redis 서버 실행
redis-server &

# Celery 작업자 실행
celery -A app.celery worker --loglevel=info --autoscale=1,1 &

# Flask 애플리케이션 실행
authbind --deep python app.py &
