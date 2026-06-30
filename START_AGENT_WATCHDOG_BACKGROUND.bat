@echo off
REM Starts the MT5 autonomous watchdog without pause prompts.
REM Use for scheduled tasks, NSSM, or a hidden background PowerShell launch.

cd /d "%~dp0"
call MT5_AGENT.bat watchdog-bg
