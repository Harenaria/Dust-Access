#!/bin/bash

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$PROJECT_ROOT" || exit

export PYTHONPATH="$PROJECT_ROOT"

poetry run python  DAMA/simulator.py "$@"
