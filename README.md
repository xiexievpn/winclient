极简win客户端，所有代码全部开源，可自行用PyInstaller打包，具体打包方法：
1，安装python 3环境，官网https://www.python.org/downloads/直接下载安装，安装务必勾选 "Add Python to PATH"
2, 以管理员身份运行windows命令行，运行curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py & python get-pip.py & pip install pyinstaller & pyinstaller --onefile --noconsole --add-data "favicon.ico;." --add-data "createplan.bat;." --add-data "close.bat;." --add-data "internet.bat;." --add-data "xray.exe;." --add-data "geoip.dat;." --add-data "geosite.dat;." main.py
3，将打包出来的exe文件连同其它文件(除main.py外)放在同一目录下即可

或者安装至少python3.2以上版本的环境，再以run.bat为入口直接使用。其中xray.exe文件可自行在官方页面下载最新版替换：https://github.com/XTLS/Xray-core/releases
