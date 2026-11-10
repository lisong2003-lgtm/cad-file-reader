@echo off
rem cad-file-reader Windows 塔吊布置识图入口：转发到 run_cad.py
python "%~dp0run_cad.py" cad_crane_geometry %*
