谢谢网络加速器，win客户端，所有代码全部开源，可自行用PyInstaller打包，具体打包方法：

1，安装python 3环境，官网https://www.python.org/downloads/ 直接下载安装，安装务必勾选 "Add Python to PATH"

2，下载25.3.6版本或当前最新版本xray.exe，并将其放在源代码目录下：https://github.com/XTLS/Xray-core/releases/tag/v25.3.6

3，以管理员身份运行windows命令行，切换到源代码目录，运行如下命令：
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py & python get-pip.py & pip install pyinstaller & pyinstaller --onefile --noconsole --add-data "favicon.ico;." --add-data "createplan.bat;." --add-data "close.bat;." --add-data "internet.bat;." --add-data "xray.exe;." --add-data "geoip.dat;." --add-data "geosite.dat;." --name "谢谢网络加速器" --icon "favicon.ico" main.py
 
4，将打包出来的exe文件连同其它文件(除main.py外)放在同一目录下运行即可
