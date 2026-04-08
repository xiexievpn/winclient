Xiexie VPN – https://xiexievpn.com

You can use PyInstaller to convert the above code into an EXE file for the Windows client of Xiexie VPN:

Install Python 3 environment, download and install directly from the official website https://www.python.org/downloads/, be sure to check "Add Python to PATH" during installation

In Windows CMD as an administrator, switch to the source code directory, then run the following command:

curl -L -o sing-box.zip https://github.com/SagerNet/sing-box/releases/download/v1.10.7/sing-box-1.10.7-windows-amd64.zip && tar -xf sing-box.zip && copy sing-box-1.10.7-windows-amd64\sing-box.exe . && curl -L -o wintun.zip https://www.wintun.net/builds/wintun-0.14.1.zip && tar -xf wintun.zip && copy wintun\bin\amd64\wintun.dll . && curl -L -o geoip-cn.srs https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-cn.srs && curl -L -o geosite-cn.srs https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-cn.srs && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python get-pip.py && pip install -r requirements.txt && pyinstaller xiexievpn.spec && rmdir /s /q sing-box-1.10.7-windows-amd64 wintun && del sing-box.zip wintun.zip get-pip.py sing-box.exe wintun.dll geoip-cn.srs geosite-cn.srs

The EXE file will be generated at: dist/
