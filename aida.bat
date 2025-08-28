@echo off
REM AIDA Assistant Launcher
REM This script ensures the correct Python environment is used

cd /d "C:\Users\huan111\OneDrive - PNNL\Desktop\AIDA"
".venv\Scripts\python.exe" -m aida.cli %*