@echo off
chcp 65001 >nul
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

:: 1) Stop sing-box first to release in-use network resources
taskkill /IM sing-box.exe >nul 2>&1
timeout /t 1 /nobreak >nul
taskkill /IM sing-box.exe /F >nul 2>&1

:: 2) Clean user proxy residue
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $p='HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'; Set-ItemProperty -Path $p -Name ProxyEnable -Value 0 -Type DWord -Force; Remove-ItemProperty -Path $p -Name ProxyServer -ErrorAction SilentlyContinue; Remove-ItemProperty -Path $p -Name AutoConfigURL -ErrorAction SilentlyContinue; Remove-ItemProperty -Path $p -Name ProxyOverride -ErrorAction SilentlyContinue } catch {}" >nul 2>&1
netsh winhttp reset proxy >nul 2>&1
ipconfig /flushdns >nul 2>&1

:: 3) Clean route/IP/DNS residue for xiexievpn only
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ifAlias='xiexievpn'; try { Get-NetRoute -InterfaceAlias $ifAlias -ErrorAction SilentlyContinue | Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue } catch {}; try { Get-NetIPAddress -InterfaceAlias $ifAlias -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue } catch {}; try { Set-DnsClientServerAddress -InterfaceAlias $ifAlias -ResetServerAddresses -ErrorAction SilentlyContinue } catch {}" >nul 2>&1

:: 4) Remove only adapters created by this client namespace (xiexievpn*)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ifAlias='xiexievpn'; try { Get-PnpDevice -Class Net -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -like ($ifAlias + '*') } | ForEach-Object { pnputil /remove-device $_.InstanceId | Out-Null } } catch {}" >nul 2>&1

exit /B 0
