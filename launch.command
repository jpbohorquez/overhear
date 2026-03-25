#!/bin/bash

# Simple runner script for the Meeting Transcription App
# Ensure setup.sh has been run at least once.

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

echo "Launching Meeting Transcription App..."
source .venv/bin/activate && python3 main.py
