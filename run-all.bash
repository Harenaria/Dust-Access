#!/bin/bash

SERVER_PORT=8080
CLIENT_PORT=8550
HOST="127.0.0.1"

cleanup() {
    kill 0
}

trap cleanup SIGINT

export PORT=$SERVER_PORT
poetry run python ./server/server.py &

sleep 2

export SERVER_HOST=$HOST
export SERVER_PORT=$SERVER_PORT
export PORT=$CLIENT_PORT
poetry run python main.py &

sleep 4

if command -v xdg-open &> /dev/null; then
    xdg-open "http://$HOST:$CLIENT_PORT"
elif command -v open &> /dev/null; then
    open "http://$HOST:$CLIENT_PORT"
else
    python3 -m webbrowser "http://$HOST:$CLIENT_PORT"
fi

wait