@echo off
chcp 65001
set arg1=%1
set mypath=%~dp0
schtasks /Create /SC ONLOGON /TN simplevpn /TR "\"%mypath%run.bat\" %arg1%" /RL HIGHEST /F
