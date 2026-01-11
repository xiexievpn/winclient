import tkinter as tk
from tkinter import messagebox, Menu, ttk
import subprocess, os, sys, ctypes
import requests
import json
import webbrowser
import platform
import urllib.parse
import win32event
import win32api
import winerror
import locale
import threading
import time
import tempfile
import shutil
from datetime import datetime

CURRENT_VERSION = "1.0.7"

proxy_state = 0            
is_manual_switching = False
pending_autostart = False
current_region = None
current_uuid = None
window = None
config_ready = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def log_debug(msg):
    """生产环境禁用日志，避免性能损耗"""
    pass

def get_system_language():
    try:
        lang_code, _ = locale.getdefaultlocale()
        if lang_code and lang_code.startswith(('zh_CN', 'zh_TW', 'zh_HK', 'zh_SG')):
            return 'zh'
        return 'en'
    except:
        return 'en'

def load_language():
    global lang_data
    try:
        with open(resource_path("languages.json"), "r", encoding="utf-8") as f:
            languages = json.load(f)
        system_lang = get_system_language()
        lang_data = languages.get(system_lang, languages['en'])
    except Exception:
        lang_data = {
            "app_title": "xiexie vpn",
            "login_title": "login",
            "login_prompt": "your access code:",
            "open_vpn": "open vpn",
            "close_vpn": "close vpn",
            "autostart": "autostart",
            "switch_region": "switch region",
            "auto_login": "automatically login next time",
            "login_button": "login",
            "copy": "copy",
            "paste": "paste",
            "select_all": "select all",
            "region_url": "https://xiexievpn.com/cn/app.html",
            "messages": {}
        }

def get_text(key):
    return lang_data.get(key, key)

def get_message(key):
    return lang_data.get("messages", {}).get(key, key)

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

load_language()

mutex_name = "XieXieVPN_SingleInstance_Mutex"
try:
    mutex = win32event.CreateMutex(None, False, mutex_name)
    last_error = win32api.GetLastError()
    if last_error == winerror.ERROR_ALREADY_EXISTS:
        messagebox.showwarning(get_text("login_title"), get_message("already_running"))
        sys.exit(0)
except Exception:
    pass

def compare_versions(version1, version2):
    try:
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]: return -1
            elif v1_parts[i] > v2_parts[i]: return 1
        return 0
    except:
        return 0

def download_file(url, local_path):
    try:
        no_proxy = {"http": None, "https": None}
        response = requests.get(url, stream=True, timeout=30, proxies=no_proxy)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception:
        return False

def check_for_updates():
    try:
        no_proxy = {"http": None, "https": None}
        response = requests.get("https://xiexievpn.com/cn/win/version.json", timeout=5, proxies=no_proxy)
        if response.status_code == 200:
            update_info = response.json()
            latest_version = update_info.get("version", "0.0.0")
            min_version = update_info.get("minVersion", "0.0.0")
            if compare_versions(CURRENT_VERSION, latest_version) < 0:
                if compare_versions(CURRENT_VERSION, min_version) < 0:
                    update_info["updateType"] = "force"
                return update_info
    except Exception:
        pass
    return None

def download_and_replace():
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'xiexievpn_new.exe')
        download_window = tk.Toplevel()
        download_window.title(get_text("app_title"))
        download_window.geometry("300x100")
        try:
            download_window.iconbitmap(resource_path("favicon.ico"))
        except:
            pass
        download_window.resizable(False, False)
        
        tk.Label(download_window, text=get_message("updating")).pack(pady=20)
        progress = ttk.Progressbar(download_window, mode='indeterminate')
        progress.pack(pady=10, padx=20, fill='x')
        progress.start()
        download_window.update()

        if not download_file("https://xiexievpn.com/cn/win/xiexievpn.exe", temp_path):
            download_window.destroy()
            messagebox.showerror("Error", get_message("download_failed"))
            return

        download_window.destroy()
        
        current_exe = sys.executable
        update_script = os.path.join(temp_dir, 'update_xiexievpn.bat')

        script_content = f'''@echo off
ping 127.0.0.1 -n 3 > nul
del /f /q "{current_exe}" 2>nul
move /y "{temp_path}" "{current_exe}" >nul
del "%~f0"
'''

        with open(update_script, 'w', encoding='gbk') as f:
            f.write(script_content)

        msg = "Update completed. The app will close now.\nPlease restart it manually."
        if get_system_language() == 'zh':
            msg = "更新已下载完成。\n\n程序将自动关闭。\n请等待几秒钟，然后手动重新打开程序以应用更新。"
            
        messagebox.showinfo(get_text("app_title"), msg)

        subprocess.Popen(update_script, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)
        
    except Exception as e:
        messagebox.showerror("Error", f"Update failed: {e}")

def show_update_dialog(update_info):
    update_type = update_info.get("updateType", "optional")
    version = update_info.get("version")
    notes = update_info.get("releaseNotes", "")
    if update_type == "force":
        messagebox.showinfo(get_message("update_required"), f"{get_message('force_update_msg')}\n\n{version}\n\n{notes}")
        download_and_replace()
    else:
        if messagebox.askyesno(get_message("update_available"), f"{get_message('optional_update_msg')}\n\n{version}\n\n{notes}"):
            download_and_replace()

def get_persistent_path(filename):
    if platform.system() == "Windows":
        appdata = os.getenv('APPDATA')
        folder = os.path.join(appdata, "XieXieVPN")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)
    else:
        home = os.path.expanduser("~")
        folder = os.path.join(home, ".XieXieVPN")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)

AUTOSTART_FILE = get_persistent_path("autostart_state.txt")

def save_autostart_state(state: bool):
    with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
        f.write("1" if state else "0")

def load_autostart_state() -> bool:
    if os.path.exists(AUTOSTART_FILE):
        with open(AUTOSTART_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() == "1"
    return False

def get_exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

exe_dir = get_exe_dir()

REGION_TO_FLAG = {
    "us-west-2": "us", "ap-northeast-2": "jp", "ap-northeast-1": "jj",
    "ap-southeast-1": "si", "ap-southeast-2": "au", "ap-south-1": "in",
    "ca-central-1": "ca", "eu-central-1": "ge", "eu-west-1": "ir",
    "eu-west-2": "ki", "eu-west-3": "fr", "eu-north-1": "sw"
}
FLAG_TO_REGION = {v: k for k, v in REGION_TO_FLAG.items()}
REGIONS = [
    ("jp", "ap-northeast-2"), ("us", "us-west-2"), ("jj", "ap-northeast-1"),
    ("in", "ap-south-1"), ("si", "ap-southeast-1"), ("au", "ap-southeast-2"),
    ("ca", "ca-central-1"), ("ge", "eu-central-1"), ("ir", "eu-west-1"),
    ("ki", "eu-west-2"), ("fr", "eu-west-3"), ("sw", "eu-north-1")
]

class RegionSelector(tk.Toplevel):
    def __init__(self, parent, current_zone, uuid):
        super().__init__(parent)
        self.parent = parent
        self.current_zone = current_zone
        self.uuid = uuid
        self.selected_flag = None
        self.switching = False
        self.max_progress = 0  
        
        self.title(get_message("select_region"))
        self.geometry("480x360")
        self.iconbitmap(resource_path("favicon.ico"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.title_label = tk.Label(main_frame, text=get_message("select_region"), font=("Arial", 14, "bold"))
        self.title_label.pack(pady=(0, 15))

        self.current_label = tk.Label(main_frame, font=("Arial", 10), fg="blue")
        self.current_label.pack(pady=(0, 10))
        
        txt = f"{get_message('current_region')}: {get_message(f'region_{current_zone}')}" if current_zone else f"{get_message('current_region')}: {get_message('region_loading')}"
        self.current_label.config(text=txt)

        self.create_flag_grid(main_frame)
        tk.Button(main_frame, text=get_message("close_button") or "Close", command=self.close_window).pack(pady=10)
    
    def force_ui_refresh(self):
        self.update_idletasks()  
        self.update()
        if sys.platform == 'win32':
            self.after(1, lambda: self.update())
    
    def create_flag_grid(self, parent):
        flag_frame = tk.Frame(parent)
        flag_frame.pack(fill=tk.BOTH, expand=True)
        self.flag_buttons = {}
        for idx, (flag_code, aws_region) in enumerate(REGIONS):
            row = idx // 4
            col = idx % 4
            btn_frame = tk.Frame(flag_frame, relief=tk.SOLID, bd=1)
            btn_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            flag_frame.grid_rowconfigure(row, weight=1)
            flag_frame.grid_columnconfigure(col, weight=1)
            try:
                flag_path = resource_path(f"flags/{flag_code}.png")
                if PIL_AVAILABLE and os.path.exists(flag_path):
                    pil_image = Image.open(flag_path).resize((40, 30), Image.Resampling.LANCZOS)
                    flag_image = ImageTk.PhotoImage(pil_image)
                    flag_label = tk.Label(btn_frame, image=flag_image, cursor="hand2")
                    flag_label.image = flag_image  
                    flag_label.pack(pady=2)
                else:
                    flag_label = tk.Label(btn_frame, text=flag_code.upper(), font=("Arial", 12, "bold"), cursor="hand2")
                    flag_label.pack(pady=2)
                
                name_label = tk.Label(btn_frame, text=get_message(f"region_{flag_code}"), font=("Arial", 8), cursor="hand2")
                name_label.pack()
                
                for w in [flag_label, name_label, btn_frame]:
                    w.bind("<Button-1>", lambda e, f=flag_code: self.on_flag_click(f))
                    
                self.flag_buttons[flag_code] = btn_frame
                if flag_code == self.current_zone:
                    self.highlight_flag(flag_code)
            except Exception: pass
    
    def highlight_flag(self, flag_code):
        for code, btn in self.flag_buttons.items():
            if code == flag_code:
                btn.config(relief=tk.RIDGE, bd=3, bg="#e8f5e9")
            else:
                btn.config(relief=tk.SOLID, bd=1, bg="SystemButtonFace")
    
    def on_flag_click(self, flag_code):
        if self.switching or flag_code == self.current_zone: return
        self.selected_flag = flag_code
        self.highlight_flag(flag_code)
        self.switch_region(flag_code)
    
    def switch_region(self, flag_code):
        global proxy_state, is_manual_switching
        is_manual_switching = True
        
        self.switching = True
        self.was_vpn_on = (proxy_state == 1)

        if self.was_vpn_on:
            try:
                subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    subprocess.run(["taskkill", "/f", "/im", "xray.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                except: pass
            except Exception: pass

        self.max_progress = 0
        self._update_progress_display(get_message("switching_region"))
        self.force_ui_refresh()
        
        for btn in self.flag_buttons.values():
            for child in btn.winfo_children():
                child.config(state="disabled")

        self.after(200, lambda: self._start_switch_thread(flag_code))
    
    def _start_switch_thread(self, flag_code):
        thread = threading.Thread(target=self._switch_region_thread, args=(flag_code,))
        thread.daemon = True
        thread.start()
    
    def _switch_region_thread(self, flag_code):
        max_retries = 2
        no_proxy = {"http": None, "https": None}
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://vvv.xiexievpn.com/switch",
                    json={"code": self.uuid, "newZone": flag_code},
                    headers={"Content-Type": "application/json"},
                    proxies=no_proxy,
                    timeout=30
                )
                if response.status_code == 200:
                    self._wait_for_config_update()
                    self.after(0, self._on_switch_success, flag_code)
                    return
                elif response.status_code in [202, 504]:
                    if self._poll_switch_status(flag_code): return
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    else:
                        self.after(0, self._on_switch_failed, "Timeout")
                        return
                else:
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    else:
                        self.after(0, self._on_switch_failed, f"HTTP {response.status_code}")
                        return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    self.after(0, self._on_switch_failed, str(e))
                    return

    def _poll_switch_status(self, flag_code):
        self.poll_attempts = 0
        self.max_poll_attempts = 120  
        self.poll_interval = 5000  
        self.target_flag_code = flag_code
        self._do_poll_attempt()
        return True
    
    def _do_poll_attempt(self):
        no_proxy = {"http": None, "https": None}
        try:
            response = requests.post("https://vvv.xiexievpn.com/getuserinfo", 
                                   json={"code": self.uuid}, 
                                   proxies=no_proxy,
                                   timeout=10)
            if response.status_code == 200:
                data = response.json()
                current_zone = data.get("zone", "")
                vmname = data.get("vmname", "")
                v2rayurl = data.get("v2rayurl", "")

                if current_zone and current_zone in REGION_TO_FLAG:
                    self._update_main_window_region(REGION_TO_FLAG[current_zone], current_zone)

                target_zone = FLAG_TO_REGION.get(self.target_flag_code, self.target_flag_code)

                if current_zone == target_zone and v2rayurl:
                    parse_and_write_config(v2rayurl)
                    self.max_progress = 100  
                    self._update_progress_display(get_message("switch_success"))
                    self.after(1000, lambda: self._on_switch_success(self.target_flag_code))
                    return
                
                if vmname and self.target_flag_code in vmname:
                    try:
                        p_resp = requests.post("https://vvv.xiexievpn.com/createvmloading", 
                                             json={"vmname": vmname}, 
                                             proxies=no_proxy,
                                             timeout=5)
                        if p_resp.status_code == 200:
                            prog = p_resp.json().get("progress", 0)
                            if prog > self.max_progress:
                                self.max_progress = prog
                                self._update_progress_display(f"{get_message('processing')}{self.max_progress}%")
                    except: pass

                if self.poll_attempts % 10 == 0:
                    est_prog = min(10 + self.poll_attempts, 90)
                    if est_prog > self.max_progress:
                        self.max_progress = est_prog
                        self._update_progress_display(f"{get_message('processing')}{self.max_progress}%")
        except: pass

        self.poll_attempts += 1
        if self.poll_attempts < self.max_poll_attempts:
            self.after(self.poll_interval, self._do_poll_attempt)
        else:
            self._on_switch_failed("Timeout")
    
    def _update_progress_display(self, text):
        try:
            color = "black" if text == get_message("switch_success") else "red"
            self.title_label.config(text=text, fg=color)
        except: pass
    
    def _wait_for_config_update(self):
        no_proxy = {"http": None, "https": None}
        for _ in range(200):
            try:
                resp = requests.post("https://vvv.xiexievpn.com/getuserinfo", 
                                   json={"code": self.uuid}, 
                                   proxies=no_proxy,
                                   timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    v2rayurl = data.get("v2rayurl", "")
                    zone = data.get("zone", "")
                    if zone: 
                        reg = REGION_TO_FLAG.get(zone, zone)
                        self.after(0, self._update_main_window_region, reg, zone)
                    if v2rayurl:
                        parse_and_write_config(v2rayurl)
                        return
            except: pass
            time.sleep(3)

    def _update_main_window_region(self, flag_code, zone):
        global current_region
        current_region = flag_code
        try:
            if 'region_label' in globals() and region_label:
                region_label.config(text=f"{get_message('current_region')}: {get_message(f'region_{flag_code}')}")
        except: pass

    def _on_switch_success(self, flag_code):
        global current_region, proxy_state, btn_general_proxy, btn_close_proxy, is_manual_switching
        
        current_region = flag_code
        self.current_zone = flag_code
        self._update_progress_display(get_message("switch_success"))
        update_region_display()

        if hasattr(self, 'was_vpn_on') and self.was_vpn_on:
            try:
                subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                proxy_state = 1
                if 'btn_general_proxy' in globals() and btn_general_proxy:
                    btn_general_proxy.config(state="disabled")
                if 'btn_close_proxy' in globals() and btn_close_proxy:
                    btn_close_proxy.config(state="normal")
            except: pass
        
        is_manual_switching = False
        self.after(2000, self.close_window)
    
    def _on_switch_failed(self, error_msg):
        global is_manual_switching
        self.title_label.config(text=get_message("select_region"), fg="black")
        for btn in self.flag_buttons.values():
            for child in btn.winfo_children():
                child.config(state="normal")
        self.highlight_flag(self.current_zone)
        self.switching = False
        is_manual_switching = False
        messagebox.showerror("Error", f"{get_message('switch_failed')}: {error_msg}")
    
    def close_window(self):
        global is_manual_switching
        is_manual_switching = False
        self.grab_release()
        self.destroy()

def open_region_selector(uuid):
    RegionSelector(window, current_region, uuid)

def update_region_display():
    global region_label, current_region
    try:
        if 'region_label' in globals() and region_label:
            txt = f"{get_message('current_region')}: {get_message(f'region_{current_region}')}" if current_region else f"{get_message('current_region')}: {get_message('region_loading')}"
            region_label.config(text=txt)
    except: pass

def toggle_autostart():
    global proxy_state
    try:
        save_autostart_state(chk_autostart.get())
        exe_path = sys.executable
        tr_value = f"\"{exe_path}\" 1"
        cmd = ["schtasks", "/Create", "/SC", "ONLOGON", "/TN", "simplevpn", "/TR", tr_value, "/RL", "HIGHEST", "/F"]
        subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        action = '/ENABLE' if chk_autostart.get() else '/DISABLE'
        subprocess.run(['schtasks', '/Change', '/TN', 'simplevpn', action], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        messagebox.showerror("Error", f"{get_message('failed_autostart')}: {e}")

def on_chk_change(*args):
    toggle_autostart()

def set_general_proxy():
    global proxy_state, config_ready
    if not config_ready and not os.path.exists(resource_path("config.json")):
        messagebox.showinfo(get_text("app_title"), get_message("config_preparing"))
        return
    try:
        subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Information", get_message("vpn_setup_success"))
        btn_general_proxy.config(state="disabled")
        btn_close_proxy.config(state="normal")
        proxy_state = 1
        toggle_autostart()
    except Exception as e:
        messagebox.showerror("Error", f"{get_message('failed_proxy')}: {e}")

def close_proxy():
    global proxy_state
    try:
        subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Information", get_message("vpn_closed"))
        btn_close_proxy.config(state="disabled")
        btn_general_proxy.config(state="normal")
        proxy_state = 0
        toggle_autostart()
    except Exception as e:
        messagebox.showerror("Error", f"{get_message('failed_close')}: {e}")

def on_closing():
    if 'btn_close_proxy' in globals() and btn_close_proxy["state"] == "normal":
        try:
            subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            messagebox.showinfo("Information", get_message("vpn_temp_closed"))
        except: pass
    window.destroy()

def save_uuid(uuid):
    with open(get_persistent_path("uuid.txt"), "w", encoding="utf-8") as f: f.write(uuid)

def load_uuid():
    path_ = get_persistent_path("uuid.txt")
    if os.path.exists(path_):
        with open(path_, "r", encoding="utf-8") as f: return f.read().strip()
    return None

def remove_uuid_file():
    path_ = get_persistent_path("uuid.txt")
    if os.path.exists(path_): os.remove(path_)

def check_login():
    entered_uuid = entry_uuid.get().strip()
    no_proxy = {"http": None, "https": None}
    try:
        response = requests.post("https://vvv.xiexievpn.com/login", json={"code": entered_uuid}, proxies=no_proxy, timeout=10)
        if response.status_code == 200:
            if chk_remember.get(): save_uuid(entered_uuid)
            login_window.destroy()
            show_main_window(entered_uuid)
        else:
            remove_uuid_file()
            msg = get_message("invalid_code") if response.status_code == 401 else get_message("expired") if response.status_code == 403 else get_message("server_error")
            messagebox.showerror("Error", msg)
    except Exception as e:
        remove_uuid_file()
        messagebox.showerror("Error", f"{get_message('connection_error')}: {e}")

def on_remember_changed(*args):
    if not chk_remember.get(): remove_uuid_file()

def do_adduser(uuid):
    no_proxy = {"http": None, "https": None}
    try: requests.post("https://vvv.xiexievpn.com/adduser", json={"code": uuid}, timeout=2, proxies=no_proxy)
    except: pass

def poll_getuserinfo(uuid):
    global current_region
    no_proxy = {"http": None, "https": None}
    try:
        response = requests.post("https://vvv.xiexievpn.com/getuserinfo", json={"code": uuid}, proxies=no_proxy, timeout=10)
        response.raise_for_status()
        data = response.json()
        v2rayurl = data.get("v2rayurl", "")
        zone = data.get("zone", "")
        if zone:
            current_region = REGION_TO_FLAG.get(zone, zone)
            update_region_display()
        if v2rayurl:
            parse_and_write_config(v2rayurl)
            return
        else:
            window.after(3000, lambda: poll_getuserinfo(uuid))
    except:
        window.after(3000, lambda: poll_getuserinfo(uuid))

def parse_and_write_config(url_string):
    try:
        if not url_string.startswith("vless://"): return
        uuid = url_string.split("@")[0].split("://")[1]
        main_part = url_string.split("@")[1]
        domain_port_part = main_part.split("?")[0]
        domain = domain_port_part.split(":")[0].split(".")[0]
        query_part = url_string.split("?")[1].split("#")[0]
        params = urllib.parse.parse_qs(query_part)
        public_key = params.get('pbk', [''])[0] or "mUzqKeHBc-s1m03iD8Dh1JoL2B9JwG5mMbimEoJ523o"
        short_id = params.get('sid', [''])[0]
        sni = params.get('sni', [f"{domain}.rocketchats.xyz"])[0].replace("www.", "")

        outbounds = [
            {"protocol": "vless", "settings": {"vnext": [{"address": f"{domain}.rocketchats.xyz", "port": 443, "users": [{"id": uuid, "encryption": "none", "flow": "xtls-rprx-vision"}]}]}, "streamSettings": {"network": "tcp", "security": "reality", "realitySettings": {"show": False, "fingerprint": "chrome", "serverName": sni, "publicKey": public_key, "shortId": short_id, "spiderX": ""}}, "tag": "proxy"},
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"}
        ]
        routing_rules = [
            {"type": "field", "domain": ["geosite:category-ads-all"], "outboundTag": "block"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "direct"},
            {"type": "field", "domain": ["geosite:geolocation-!cn"], "outboundTag": "proxy"},
            {"type": "field", "ip": ["geoip:cn", "geoip:private"], "outboundTag": "direct"}
        ]
        config_data = {
            "log": {"loglevel": "none", "error": ""},
            "dns": {"servers": [{"tag": "bootstrap", "address": "223.5.5.5", "domains": [], "detour": "direct"}, {"tag": "remote-doh", "address": "https://1.1.1.1/dns-query", "detour": "proxy"}], "queryStrategy": "UseIPv4"},
            "routing": {"domainStrategy": "IPIfNonMatch", "rules": routing_rules},
            "inbounds": [{"listen": "127.0.0.1", "port": 10808, "protocol": "socks"}, {"listen": "127.0.0.1", "port": 1080, "protocol": "http"}],
            "outbounds": outbounds
        }
        with open(resource_path("config.json"), "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

        global config_ready, pending_autostart
        config_ready = True
        
        if pending_autostart:
            pending_autostart = False
            set_general_proxy()
        
        if 'btn_general_proxy' in globals() and btn_general_proxy and proxy_state == 0:
            btn_general_proxy.config(state="normal")
            
    except Exception as e:
        messagebox.showerror("Error", f"{get_message('config_error')}: {e}")

def fetch_config_data(uuid):
    global current_region
    no_proxy = {"http": None, "https": None}
    try:
        response = requests.post("https://vvv.xiexievpn.com/getuserinfo", json={"code": uuid}, proxies=no_proxy, timeout=10)
        response.raise_for_status()
        data = response.json()
        v2rayurl = data.get("v2rayurl", "")
        zone = data.get("zone", "")
        if zone:
            current_region = REGION_TO_FLAG.get(zone, zone)
            update_region_display()
        if not v2rayurl and not zone:
            do_adduser(uuid)
            window.after(10, lambda: poll_getuserinfo(uuid))
        elif not v2rayurl:
            window.after(10, lambda: poll_getuserinfo(uuid))
        else:
            parse_and_write_config(v2rayurl)
    except Exception as e:
        messagebox.showerror("Error", f"{get_message('connection_error')}: {e}")

def check_proxy_connectivity():
    proxies = {'http': 'http://127.0.0.1:1080', 'https': 'http://127.0.0.1:1080'}
    try:
        if requests.get("http://www.google.com/generate_204", proxies=proxies, timeout=5).status_code == 204:
            return True
        return False
    except:
        return False

def check_local_network():
    try:
        requests.get("https://www.baidu.com", proxies={"http": None, "https": None}, timeout=5)
        return True
    except:
        return False

def perform_silent_recovery(v2rayurl, zone):
    global current_region, proxy_state, btn_general_proxy, btn_close_proxy
    
    if zone:
        current_region = REGION_TO_FLAG.get(zone, zone)
        update_region_display()
    
    try:
        parse_and_write_config(v2rayurl)
    except: return

    if proxy_state == 1:
        try:
            subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(1)
            subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            toggle_autostart()
            
            if 'btn_general_proxy' in globals() and btn_general_proxy:
                btn_general_proxy.config(state="disabled")
            if 'btn_close_proxy' in globals() and btn_close_proxy:
                btn_close_proxy.config(state="normal")
        except: pass

def connection_watchdog_thread(uuid):
    """后台监控线程"""
    global proxy_state, window, is_manual_switching
    
    fail_count = 0
    check_interval = 15 
    no_proxy = {"http": None, "https": None}
    
    while True:
        time.sleep(check_interval)

        # [关键修复] 如果用户正在手动换区，跳过检测
        if is_manual_switching:
            continue

        if proxy_state == 1:
            if not check_proxy_connectivity():
                fail_count += 1
                if fail_count >= 2:
                    if check_local_network():
                        # 本地有网，代理不通 -> 尝试静默自愈
                        try:
                            # 强制直连获取配置
                            resp = requests.post("https://vvv.xiexievpn.com/getuserinfo", 
                                               json={"code": uuid}, 
                                               proxies=no_proxy, 
                                               timeout=10)
                            if resp.status_code == 200:
                                data = resp.json()
                                new_url = data.get("v2rayurl", "")
                                new_zone = data.get("zone", "")
                                if new_url:
                                    if window:
                                        window.after(0, lambda: perform_silent_recovery(new_url, new_zone))
                                    fail_count = 0
                                    time.sleep(15) 
                        except: pass
            else:
                fail_count = 0

# ================= 主窗口启动 =================

def show_main_window(uuid):
    global window, btn_general_proxy, btn_close_proxy, chk_autostart, current_uuid, region_label
    current_uuid = uuid
    window = tk.Tk()
    window.title(get_text("app_title"))
    window.geometry("300x320")
    window.iconbitmap(resource_path("favicon.ico"))
    window.protocol("WM_DELETE_WINDOW", on_closing)

    btn_general_proxy = tk.Button(window, text=get_text("open_vpn"), command=set_general_proxy)
    btn_close_proxy = tk.Button(window, text=get_text("close_vpn"), command=close_proxy)

    if not config_ready and not os.path.exists(resource_path("config.json")):
        btn_general_proxy.config(state="disabled")
    
    # 初始状态下关闭按钮通常禁用
    btn_close_proxy.config(state="disabled")
    
    btn_general_proxy.pack(pady=10)
    btn_close_proxy.pack(pady=10)

    chk_autostart = tk.BooleanVar()
    chk_autostart.set(load_autostart_state())
    chk_autostart.trace_add("write", on_chk_change)
    tk.Checkbutton(window, text=get_text("autostart"), variable=chk_autostart, command=toggle_autostart).pack(pady=10)

    tk.Button(window, text=get_text("switch_region"), command=lambda: open_region_selector(uuid)).pack(pady=10)
    region_label = tk.Label(window, text="", font=("Arial", 9), fg="gray")
    region_label.pack(pady=5)

    fetch_config_data(uuid)
    window.after(1000, update_region_display)

    def check_update_async():
        def update_check():
            update_info = check_for_updates()
            if update_info:
                window.after(0, lambda: show_update_dialog(update_info))
        threading.Thread(target=update_check, daemon=True).start()
        
    window.after(3000, check_update_async)

    # 启动修复后的监控线程
    monitor_thread = threading.Thread(target=connection_watchdog_thread, args=(uuid,), daemon=True)
    monitor_thread.start()
    
    if len(sys.argv) > 1:
        try:
            if int(sys.argv[1]) == 1:
                global pending_autostart
                if config_ready: set_general_proxy()
                else: pending_autostart = True  
        except: pass

    window.deiconify()
    window.attributes('-topmost', True)
    window.attributes('-topmost', False)     
    window.mainloop()

login_window = tk.Tk()
login_window.title(get_text("login_title"))
login_window.geometry("300x200")
login_window.iconbitmap(resource_path("favicon.ico"))

tk.Label(login_window, text=get_text("login_prompt")).pack(pady=10)
entry_uuid = tk.Entry(login_window)
entry_uuid.pack(pady=5)
entry_uuid.bind("<Control-Key-a>", lambda event: entry_uuid.select_range(0, tk.END))

menu = Menu(entry_uuid, tearoff=0)
menu.add_command(label=get_text("copy"), command=lambda: login_window.clipboard_append(entry_uuid.selection_get()))
menu.add_command(label=get_text("paste"), command=lambda: entry_uuid.insert(tk.INSERT, login_window.clipboard_get()))
menu.add_command(label=get_text("select_all"), command=lambda: entry_uuid.select_range(0, tk.END))
entry_uuid.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

chk_remember = tk.BooleanVar()
tk.Checkbutton(login_window, text=get_text("auto_login"), variable=chk_remember).pack(pady=5)
chk_remember.trace_add("write", on_remember_changed)
tk.Button(login_window, text=get_text("login_button"), command=check_login).pack(pady=10)

if saved_uuid := load_uuid():
    entry_uuid.insert(0, saved_uuid)
    check_login()

login_window.mainloop()
