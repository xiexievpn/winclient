@echo off
chcp 65001
:: BatchGotAdmin
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' ( goto UACPrompt ) else ( goto gotAdmin )
:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B
:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"

:: 尝试正常关闭 sing-box 以释放虚拟网卡
taskkill /IM sing-box.exe >nul 2>&1
timeout /t 1 /nobreak >nul
:: 兜底强杀
taskkill /IM sing-box.exe /F >nul 2>&1

:: 兼容旧版本用户直升，清除注册表残留（建议保留几个版本后再删除）
powershell -Command "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0" >nul 2>&1
exit /B