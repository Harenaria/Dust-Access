#!/bin/bash
source ./.venv/bin/activate && python -m server.server &

x-terminal-emulator -e bash -c "source ./.venv/bin/activate && python -m main; exec bash" &
x-terminal-emulator -e bash -c "source ./.venv/bin/activate && python -m main; exec bash" &