FROM python:3.12-slim
WORKDIR /app
VOLUME [ "/app/logs" ]
VOLUME [ "/app/config.json" ]
EXPOSE 9000
COPY server.py .
COPY formatters.py .
COPY handlers.py .
CMD [ "python" , "server.py"]
