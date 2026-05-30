@echo off
REM Build a Windows executable using PyInstaller.
REM Run this from the repository root with your virtualenv active.

pyinstaller --noconfirm --windowed --onefile --name video-extractor main.py
pause
