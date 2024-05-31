@if (@CodeSection == @Batch) @then
@echo off
chcp 65001
:: BatchGotAdmin (Run as Admin code starts)
REM --> Check for permissions
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )
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
:: BatchGotAdmin (Run as Admin code ends)
cscript /nologo /e:JScript "%~f0" ".\xray.exe" "-c" ".\config.json"
powershell -Command "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 1"
powershell -Command "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value 'localhost:1080'"
exit /B
@end
var shell = WScript.CreateObject("WScript.Shell");
var args = WScript.Arguments;
shell.Run(args(0) + " " + args(1) + " " + args(2), 0, false);