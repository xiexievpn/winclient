import tkinter as tk
from tkinter import messagebox
import subprocess, os, sys, ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit(0)

def get_exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


exe_dir = get_exe_dir()
os.chdir(exe_dir)

def toggle_autostart():
    global proxy_state
    subprocess.run(["cmd", "/c", "createplan.bat", str(proxy_state)])
    if chk_autostart.get():
        subprocess.run(['schtasks', '/Change', '/TN', 'simplevpn', '/ENABLE'])
    else:
        subprocess.run(['schtasks', '/Change', '/TN', 'simplevpn', '/DISABLE'])


def set_general_proxy():
    global proxy_state
    subprocess.run(["cmd", "/c", "close.bat"])
    subprocess.run(["cmd", "/c", "internet.bat"])
    messagebox.showinfo("Information", "加速设置成功")
    btn_general_proxy.config(state="disabled")
    btn_close_proxy.config(state="normal")
    proxy_state = 1
    toggle_autostart()


def close_proxy():
    global proxy_state
    subprocess.run(["cmd", "/c", "close.bat"])
    messagebox.showinfo("Information", "加速已关闭")
    btn_close_proxy.config(state="disabled")
    btn_general_proxy.config(state="normal")
    proxy_state = 0
    toggle_autostart()


def on_closing():
    close_state = btn_close_proxy["state"]
    general_state = btn_general_proxy["state"]
    if close_state == "normal":
        if general_state == "disabled":
            subprocess.run(["cmd", "/c", "close.bat"])
            messagebox.showinfo("Information", "加速已暂时关闭")
    window.destroy()


window = tk.Tk()
window.title("简约网络加速器")
window.geometry("300x200")
window.iconbitmap("favicon.ico")
proxy_state = 0
chk_autostart = tk.BooleanVar()
result = subprocess.run(["schtasks", "/Query", "/TN", "simplevpn"], stdout=(subprocess.PIPE), stderr=(subprocess.PIPE))
if "ERROR: The system cannot find the file specified." not in result.stderr.decode(errors="ignore"):
    chk_autostart.set(True)
window.protocol("WM_DELETE_WINDOW", on_closing)
btn_general_proxy = tk.Button(window, text="打开加速", command=set_general_proxy)
btn_close_proxy = tk.Button(window, text="关闭加速", command=close_proxy)
btn_general_proxy.pack(pady=20)
btn_close_proxy.pack(pady=20)
chk_autostart = tk.BooleanVar()
chk_autostart_button = tk.Checkbutton(window, text="开机自启动", variable=chk_autostart, command=toggle_autostart)
chk_autostart_button.pack(pady=20)
if len(sys.argv) > 1:
    chk_autostart.set(True)
    try:
        start_state = int(sys.argv[1])
        if start_state == 1:
            set_general_proxy()
    except ValueError:
        pass

window.mainloop()
