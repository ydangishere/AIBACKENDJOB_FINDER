@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py" 2>nul
if errorlevel 1 "%~dp0.venv\Scripts\python.exe" "%~dp0app.py"
