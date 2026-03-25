@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv" (
    echo Virtual environment not found. Please run the Windows installation steps in README.md first.
    pause
    exit /b 1
)

echo Launching Meeting Transcription App...
call .venv\Scripts\activate.bat
python main.py
endlocal
