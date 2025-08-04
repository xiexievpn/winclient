谢谢网络加速器，win客户端，所有代码全部开源，可自行用PyInstaller打包，具体打包方法：

1，安装python 3环境，官网https://www.python.org/downloads/ 直接下载安装，安装务必勾选 "Add Python to PATH"

2，以管理员身份运行windows命令行，切换到源代码目录，运行如下命令：
curl -L -o Xray-windows-64.zip https://github.com/XTLS/Xray-core/releases/download/v25.3.6/Xray-windows-64.zip && tar -xf Xray-windows-64.zip xray.exe geoip.dat geosite.dat && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python get-pip.py && pip install pyinstaller && pyinstaller --onefile --noconsole --add-data "favicon.ico;." --add-data "close.bat;." --add-data "internet.bat;." --add-data "xray.exe;." --add-data "geoip.dat;." --add-data "geosite.dat;." --name "谢谢网络加速器" --icon "favicon.ico" main.py && del Xray-windows-64.zip get-pip.py xray.exe geoip.dat geosite.dat
