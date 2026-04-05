@if (@CodeSection == @Batch) @then
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

cscript /nologo /e:JScript "%~f0" ".\sing-box.exe" "run" "-c" ".\config.json"
exit /B
@end
var shell = WScript.CreateObject("WScript.Shell");
var args = WScript.Arguments;
shell.Run('"' + args(0) + '" "' + args(1) + '" "' + args(2) + '" "' + args(3) + '"', 0, false);