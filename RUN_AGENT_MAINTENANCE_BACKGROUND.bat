@echo off
REM Runs maintenance once without pause prompts. Safe for Task Scheduler.

cd /d "%~dp0"
call MT5_AGENT.bat maintenance-bg
