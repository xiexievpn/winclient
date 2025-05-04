import tkinter as tk
from tkinter import messagebox, Menu
import subprocess, os, sys, ctypes
import requests
import json
import webbrowser

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

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

proxy_state = 0

def toggle_autostart():
    global proxy_state
    try:
        result = subprocess.run(["cmd", "/c", resource_path("createplan.bat"), str(proxy_state)], capture_output=True, text=True, check=True)
        if chk_autostart.get():
            subprocess.run(['schtasks', '/Change', '/TN', 'simplevpn', '/ENABLE'], capture_output=True, text=True, check=True)
        else:
            subprocess.run(['schtasks', '/Change', '/TN', 'simplevpn', '/DISABLE'], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to modify autostart task: {e.stderr}\nReturn code: {e.returncode}")

def on_chk_change(*args):
    toggle_autostart()

def set_general_proxy():
    global proxy_state
    try:
        subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, text=True, check=True)
        subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, text=True, check=True)
        messagebox.showinfo("Information", "加速设置成功")
        btn_general_proxy.config(state="disabled")
        btn_close_proxy.config(state="normal")
        proxy_state = 1
        toggle_autostart()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to set general proxy: {e.stderr}")

def close_proxy():
    global proxy_state
    try:
        subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, text=True, check=True)
        messagebox.showinfo("Information", "加速已关闭")
        btn_close_proxy.config(state="disabled")
        btn_general_proxy.config(state="normal")
        proxy_state = 0
        toggle_autostart()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to close proxy: {e.stderr}")

def on_closing():
    close_state = btn_close_proxy["state"]
    general_state = btn_general_proxy["state"]
    if close_state == "normal":
        if general_state == "disabled":
            try:
                subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, text=True, check=True)
                messagebox.showinfo("Information", "加速已暂时关闭")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to close proxy on exit: {e.stderr}")
    window.destroy()

def save_uuid(uuid):
    with open("uuid.txt", "w") as file:
        file.write(uuid)

def load_uuid():
    if os.path.exists("uuid.txt"):
        with open("uuid.txt", "r") as file:
            return file.read().strip()
    return None

def check_login():
    entered_uuid = entry_uuid.get().strip()
    try:
        response = requests.post("https://vvv.xiexievpn.com/login", json={"code": entered_uuid})
        if response.status_code == 200:
            # 登录成功，保存UUID并关闭登录窗口显示主窗口
            if chk_remember.get():
                save_uuid(entered_uuid)
            login_window.destroy()
            # 将用户输入的 UUID 传递给主窗口函数
            show_main_window(entered_uuid)
        elif response.status_code == 401:
            messagebox.showerror("Error", "无效的随机码")
        elif response.status_code == 403:
            messagebox.showerror("Error", "访问已过期")
        else:
            messagebox.showerror("Error", "服务器错误")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"无法连接到服务器: {e}")

def do_adduser(uuid):
    try:
        requests.post(
            "https://vvv.xiexievpn.com/adduser",
            json={"code": uuid},
            timeout=2
        )
    except requests.exceptions.RequestException as e:
        print(f"调用 /adduser 出错或超时(可忽略)：{e}")

def poll_getuserinfo(uuid):
    try:
        response = requests.post(
            "https://vvv.xiexievpn.com/getuserinfo",
            json={"code": uuid},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        response_data = response.json()
        v2rayurl = response_data.get("v2rayurl", "")
        zone = response_data.get("zone", "")

        if v2rayurl:
            parse_and_write_config(v2rayurl)
            return
        else:
            window.after(3000, lambda: poll_getuserinfo(uuid))

    except requests.exceptions.RequestException as e:
        window.after(3000, lambda: poll_getuserinfo(uuid))

def parse_and_write_config(url_string):
    try:
        # 以 vless:// 开头
        if not url_string.startswith("vless://"):
            messagebox.showerror("Error", "服务器返回的数据不符合预期格式（不是 vless:// 开头）")
            return

        uuid = url_string.split("@")[0].split("://")[1]
        domain = url_string.split("@")[1].split(":")[0].split(".")[0]
        jsonport_string = url_string.split(":")[2].split("?")[0]
        jsonport = int(jsonport_string)
        sni = url_string.split("sni=")[1].split("#")[0].replace("www.", "")

        config_data = {
            "log": {
                "loglevel": "error"
            },
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {
                        "type": "field",
                        "domain": ["geosite:category-ads-all"],
                        "outboundTag": "block"
                    },
                    {
                        "type": "field",
                        "protocol": ["bittorrent"],
                        "outboundTag": "direct"
                    },
                    {
                        "type": "field",
                        "domain": ["geosite:geolocation-!cn"],
                        "outboundTag": "proxy"
                    },
                    {
                        "type": "field",
                        "ip": ["geoip:cn", "geoip:private"],
                        "outboundTag": "proxy"
                    }
                ]
            },
            "inbounds": [
                {
                    "listen": "127.0.0.1",
                    "port": 10808,
                    "protocol": "socks"
                },
                {
                    "listen": "127.0.0.1",
                    "port": 1080,
                    "protocol": "http"
                }
            ],
            "outbounds": [
                {
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": f"{domain}.rocketchats.xyz",
                                "port": 443,
                                "users": [
                                    {
                                        "id": uuid,
                                        "encryption": "none",
                                        "flow": "xtls-rprx-vision"
                                    }
                                ]
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "show": False,
                            "fingerprint": "chrome",
                            "serverName": f"{domain}.rocketchats.xyz",
                            "publicKey": "mUzqKeHBc-s1m03iD8Dh1JoL2B9JwG5mMbimEoJ523o",
                            "shortId": "",
                            "spiderX": ""
                        }
                    },
                    "tag": "proxy"
                },
                {
                    "protocol": "freedom",
                    "tag": "direct"
                },
                {
                    "protocol": "blackhole",
                    "tag": "block"
                }
            ]
        }

        with open(resource_path("config.json"), "w", encoding="utf-8") as config_file:
            json.dump(config_data, config_file, indent=4)

    except Exception as e:
        print(f"提取配置信息时发生错误: {e}")
        messagebox.showerror("Error", f"提取配置信息时发生错误: {e}")

def fetch_config_data(uuid):
    try:
        response = requests.post(
            "https://vvv.xiexievpn.com/getuserinfo",
            json={"code": uuid},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        response_data = response.json()
        v2rayurl = response_data.get("v2rayurl", "")
        zone = response_data.get("zone", "")

        if not v2rayurl and not zone:
            print("v2rayurl 和 zone 都为空，先调用 /adduser...")
            do_adduser(uuid)
            window.after(10, lambda: poll_getuserinfo(uuid))

        elif not v2rayurl:
            window.after(10, lambda: poll_getuserinfo(uuid))

        else:
            parse_and_write_config(v2rayurl)

    except requests.exceptions.RequestException as e:
        print(f"无法连接到服务器: {e}")
        messagebox.showerror("Error", f"无法连接到服务器: {e}")

def show_main_window(uuid):
    global window, btn_general_proxy, btn_close_proxy, chk_autostart
    window = tk.Tk()
    window.title("谢谢网络加速器")
    window.geometry("300x250")
    window.iconbitmap(resource_path("favicon.ico"))

    window.protocol("WM_DELETE_WINDOW", on_closing)

    btn_general_proxy = tk.Button(window, text="打开加速", command=set_general_proxy)
    btn_close_proxy = tk.Button(window, text="关闭加速", command=close_proxy)
    btn_general_proxy.pack(pady=10)
    btn_close_proxy.pack(pady=10)

    chk_autostart = tk.BooleanVar()
    chk_autostart.trace_add("write", on_chk_change)
    try:
        result = subprocess.run(["schtasks", "/Query", "/TN", "simplevpn"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if "Enabled" in result.stdout:
            chk_autostart.set(True)
        else:
            chk_autostart.set(False)
    except subprocess.CalledProcessError:
        chk_autostart.set(False)

    chk_autostart_button = tk.Checkbutton(window, text="开机自启动", variable=chk_autostart, command=toggle_autostart)
    chk_autostart_button.pack(pady=10)

    # 添加“切换区域”的超链接
    lbl_switch_region = tk.Label(window, text="切换区域", fg="blue", cursor="hand2")
    lbl_switch_region.pack(pady=5)
    lbl_switch_region.bind("<Button-1>", lambda event: (
        messagebox.showinfo("切换区域", "切换区域后需重启此应用程序"),
        webbrowser.open(f"https://v.getsteamcard.com/app.html?code={uuid}")
    ))

    # 在主窗口显示时，调用 fetch_config_data() 并传递用户输入的 uuid
    fetch_config_data(uuid)

    if len(sys.argv) > 1:
        try:
            start_state = int(sys.argv[1])
            if start_state == 1:
                set_general_proxy()
        except ValueError:
            pass

    window.deiconify()
    window.attributes('-topmost', True)
    window.attributes('-topmost', False)     

    window.mainloop()

# Login window
login_window = tk.Tk()
login_window.title("登录")
login_window.geometry("300x200")
login_window.iconbitmap(resource_path("favicon.ico"))

label_uuid = tk.Label(login_window, text="请输入随机码:")
label_uuid.pack(pady=10)

entry_uuid = tk.Entry(login_window)
entry_uuid.pack(pady=5)
entry_uuid.bind("<Control-Key-a>", lambda event: entry_uuid.select_range(0, tk.END))  # 允许全选
entry_uuid.bind("<Control-Key-c>", lambda event: login_window.clipboard_append(entry_uuid.selection_get()))  # 允许复制
entry_uuid.bind("<Control-Key-v>", lambda event: entry_uuid.insert(tk.INSERT, login_window.clipboard_get()))  # 允许粘贴

menu = Menu(entry_uuid, tearoff=0)
menu.add_command(label="复制", command=lambda: login_window.clipboard_append(entry_uuid.selection_get()))
menu.add_command(label="粘贴", command=lambda: entry_uuid.insert(tk.INSERT, login_window.clipboard_get()))
menu.add_command(label="全选", command=lambda: entry_uuid.select_range(0, tk.END))

def show_context_menu(event):
    menu.post(event.x_root, event.y_root)

entry_uuid.bind("<Button-3>", show_context_menu)  # 绑定右键菜单

chk_remember = tk.BooleanVar()
chk_remember_button = tk.Checkbutton(login_window, text="下次自动登录", variable=chk_remember)
chk_remember_button.pack(pady=5)

btn_login = tk.Button(login_window, text="登录", command=check_login)
btn_login.pack(pady=10)

# 自动填充已保存的 UUID 并尝试自动登录
saved_uuid = load_uuid()
if saved_uuid:
    entry_uuid.insert(0, saved_uuid)
    check_login()

login_window.mainloop()
