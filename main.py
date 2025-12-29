import tkinter as tk
from tkinter import messagebox, Menu, ttk
import subprocess, os, sys, ctypes
import requests
import json
import webbrowser
import platform
import urllib.parse
import locale
import threading
import time
import tempfile
import shutil

# 版本常量
CURRENT_VERSION = "1.0.4"

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available, using text labels for flags")

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
    except Exception as e:
        print(f"Error loading language file: {e}")
        lang_data = {
            "app_title": "xiexie vpn",
            "login_title": "Login",
            "login_prompt": "Your access code:",
            "open_vpn": "Connect",
            "close_vpn": "Disconnect",
            "autostart": "Auto Start",
            "switch_region": "Switch Region",
            "auto_login": "Auto Login",
            "login_button": "Login",
            "copy": "copy",
            "paste": "paste",
            "select_all": "select all",
            "region_url": "https://xiexievpn.com/app.html",
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
    params = " ".join(sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)

load_language()

mutex_name = "XieXieVPN_SingleInstance_Mutex"
kernel32 = ctypes.windll.kernel32
mutex = None

def acquire_mutex():
    global mutex
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    
    if last_error == 183:
        return False
    return True

if not acquire_mutex():
    sys.exit(0)

# 版本比较函数
def compare_versions(version1, version2):
    """比较两个版本号，返回 -1（v1<v2）、0（v1=v2）或 1（v1>v2）"""
    try:
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        # 补齐长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))

        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        return 0
    except:
        return 0

def download_file(url, local_path):
    """下载文件"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def check_for_updates():
    """检查更新"""
    try:
        response = requests.get(f"https://xiexievpn.com/cn/win/version.json?t={int(time.time())}", timeout=5)
        if response.status_code == 200:
            update_info = response.json()
            latest_version = update_info.get("version", "0.0.0")
            min_version = update_info.get("minVersion", "0.0.0")

            if compare_versions(CURRENT_VERSION, latest_version) < 0:
                # 判断是否强制更新
                if compare_versions(CURRENT_VERSION, min_version) < 0:
                    update_info["updateType"] = "force"
                return update_info
    except Exception as e:
        print(f"Update check failed: {e}")
    return None

def download_and_replace():
    global mutex
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'xiexievpn_new.exe')

        download_window = tk.Toplevel()
        download_window.title(get_text("app_title"))
        download_window.geometry("300x100")
        try:
            download_window.iconbitmap(resource_path("favicon.ico"))
        except: pass
        download_window.resizable(False, False)

        label = tk.Label(download_window, text=get_message("updating") or "Updating...")
        label.pack(pady=20)
        progress = ttk.Progressbar(download_window, mode='indeterminate')
        progress.pack(pady=10, padx=20, fill='x')
        progress.start()
        download_window.update()

        if not download_file("https://xiexievpn.com/win/xiexievpn.exe", temp_path):
            download_window.destroy()
            messagebox.showerror("Error", get_message("download_failed") or "Download failed")
            return

        download_window.destroy()

        current_exe = sys.executable
        update_script = os.path.join(temp_dir, 'update_xiexievpn.bat')
        current_dir = os.path.dirname(current_exe)

        script_content = f'''@echo off
chcp 65001 > nul
echo Updating XieXieVPN...

:loop
ping 127.0.0.1 -n 2 > nul
del /f /q "{current_exe}" 2>nul
if exist "{current_exe}" goto loop

echo Moving new file...
move /y "{temp_path}" "{current_exe}" >nul

echo Restarting...
cd /d "{current_dir}"
start "" "{current_exe}" 1

del "%~f0"
'''
        with open(update_script, 'w', encoding='gbk') as f:
            f.write(script_content)

        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)
            mutex = None
        
        # 启动更新脚本
        subprocess.Popen(update_script, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        # 立即强制退出，不等待清理，防止死锁
        os._exit(0)

    except Exception as e:
        print(f"Update failed: {e}")
        messagebox.showerror("Error", f"Update failed: {e}")


def show_update_dialog(update_info):
    update_type = update_info.get("updateType", "optional")
    version = update_info.get("version")
    notes = update_info.get("releaseNotes", "")

    msg = f"{get_message('version_label') or 'Version'}: {version}\n\n{notes}"

    if update_type == "force":
        messagebox.showinfo(get_message("update_required") or "Update Required", msg)
        download_and_replace()
    else:
        result = messagebox.askyesno(get_message("update_available") or "Update Available", msg)
        if result:
            download_and_replace()

# 全局状态变量
config_ready = False        # 标记config.json是否已创建
pending_autostart = False   # 标记是否需要自动启动
current_region = None       # 当前区域
current_uuid = None         # 当前用户UUID

def get_persistent_path(filename):
    if platform.system() == "Windows":
        appdata = os.getenv('APPDATA')
        your_app_folder = os.path.join(appdata, "XieXieVPN")
        os.makedirs(your_app_folder, exist_ok=True)
        return os.path.join(your_app_folder, filename)
    else:
        home = os.path.expanduser("~")
        your_app_folder = os.path.join(home, ".XieXieVPN")
        os.makedirs(your_app_folder, exist_ok=True)
        return os.path.join(your_app_folder, filename)

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

proxy_state = 0

# 区域映射配置
REGION_TO_FLAG = {
    "us-west-2": "us",
    "ap-northeast-2": "jp", 
    "ap-northeast-1": "jj",
    "ap-southeast-1": "si",
    "ap-southeast-2": "au",
    "ap-south-1": "in",
    "ca-central-1": "ca",
    "eu-central-1": "ge",
    "eu-west-1": "ir",
    "eu-west-2": "ki",
    "eu-west-3": "fr",
    "eu-north-1": "sw"
}

FLAG_TO_REGION = {v: k for k, v in REGION_TO_FLAG.items()}

# 区域配置：(flag_code, region_aws_code)
REGIONS = [
    ("jp", "ap-northeast-2"),
    ("us", "us-west-2"), 
    ("jj", "ap-northeast-1"),
    ("in", "ap-south-1"),
    ("si", "ap-southeast-1"),
    ("au", "ap-southeast-2"),
    ("ca", "ca-central-1"),
    ("ge", "eu-central-1"),
    ("ir", "eu-west-1"),
    ("ki", "eu-west-2"),
    ("fr", "eu-west-3"),
    ("sw", "eu-north-1")
]

class RegionSelector(tk.Toplevel):
    def __init__(self, parent, current_zone, uuid):
        super().__init__(parent)
        self.parent = parent
        self.current_zone = current_zone
        self.uuid = uuid
        self.selected_flag = None
        self.switching = False
        self.max_progress = 0  # 跟踪最大进度值，确保进度只增不减
        
        self.title(get_message("select_region"))
        self.geometry("480x360")
        self.iconbitmap(resource_path("favicon.ico"))
        self.resizable(False, False)
        
        # 使窗口居中
        self.transient(parent)
        self.grab_set()
        
        # 创建主框架
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        self.title_label = tk.Label(main_frame, text=get_message("select_region"), 
                              font=("Arial", 14, "bold"))
        self.title_label.pack(pady=(0, 15))
        
        # 当前区域显示（始终显示）
        self.current_label = tk.Label(main_frame, font=("Arial", 10), fg="blue")
        self.current_label.pack(pady=(0, 10))
        
        if current_zone:
            current_text = f"{get_message('current_region')}: {get_message(f'region_{current_zone}')}"
        else:
            current_text = f"{get_message('current_region')}: {get_message('region_loading')}"
        self.current_label.config(text=current_text)
        
        # 创建国旗网格
        self.create_flag_grid(main_frame)
        
        # 进度将通过窗口标题显示，不需要UI组件
        
        # 关闭按钮
        close_btn = tk.Button(main_frame, text=get_message("close_button") if get_message("close_button") else "Close", 
                             command=self.close_window)
        close_btn.pack(pady=10)
    
    def force_ui_refresh(self):
        """强制刷新UI，确保进度条等元素立即显示"""
        self.update_idletasks()  # 处理待定的几何管理
        self.update()  # 处理所有待定事件
        # Windows特定：使用after延迟确保渲染
        if sys.platform == 'win32':
            self.after(1, lambda: self.update())
    
    def create_flag_grid(self, parent):
        # 创建滚动框架
        flag_frame = tk.Frame(parent)
        flag_frame.pack(fill=tk.BOTH, expand=True)
        
        # 4列3行布局
        self.flag_buttons = {}
        for idx, (flag_code, aws_region) in enumerate(REGIONS):
            row = idx // 4
            col = idx % 4
            
            # 创建按钮框架
            btn_frame = tk.Frame(flag_frame, relief=tk.SOLID, bd=1)
            btn_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            
            # 配置网格权重
            flag_frame.grid_rowconfigure(row, weight=1)
            flag_frame.grid_columnconfigure(col, weight=1)
            
            try:
                # 加载国旗图片
                flag_path = resource_path(f"flags/{flag_code}.png")
                if PIL_AVAILABLE and os.path.exists(flag_path):
                    # 加载并调整图片大小
                    pil_image = Image.open(flag_path)
                    pil_image = pil_image.resize((40, 30), Image.Resampling.LANCZOS)
                    flag_image = ImageTk.PhotoImage(pil_image)
                    
                    # 创建图片标签
                    flag_label = tk.Label(btn_frame, image=flag_image, cursor="hand2")
                    flag_label.image = flag_image  # 保持引用
                    flag_label.pack(pady=2)
                else:
                    # 如果PIL不可用或图片不存在，显示文字
                    flag_label = tk.Label(btn_frame, text=flag_code.upper(), 
                                        font=("Arial", 12, "bold"), cursor="hand2")
                    flag_label.pack(pady=2)
                
                # 区域名称
                region_name = get_message(f"region_{flag_code}")
                name_label = tk.Label(btn_frame, text=region_name, 
                                    font=("Arial", 8), cursor="hand2")
                name_label.pack()
                
                # 绑定点击事件
                flag_label.bind("<Button-1>", lambda e, f=flag_code: self.on_flag_click(f))
                name_label.bind("<Button-1>", lambda e, f=flag_code: self.on_flag_click(f))
                btn_frame.bind("<Button-1>", lambda e, f=flag_code: self.on_flag_click(f))
                
                # 保存按钮引用
                self.flag_buttons[flag_code] = btn_frame
                
                # 高亮当前区域
                if flag_code == self.current_zone:
                    self.highlight_flag(flag_code)
                    
            except Exception as e:
                print(f"Error loading flag {flag_code}: {e}")
                # 创建文字按钮作为备用
                text_label = tk.Label(btn_frame, text=flag_code.upper(), 
                                    font=("Arial", 10, "bold"), cursor="hand2")
                text_label.pack()
                text_label.bind("<Button-1>", lambda e, f=flag_code: self.on_flag_click(f))
                self.flag_buttons[flag_code] = btn_frame
                
                if flag_code == self.current_zone:
                    self.highlight_flag(flag_code)
    
    def highlight_flag(self, flag_code):
        # 移除之前的高亮
        for code, btn in self.flag_buttons.items():
            if code == flag_code:
                btn.config(relief=tk.RIDGE, bd=3, bg="#e8f5e9")
            else:
                btn.config(relief=tk.SOLID, bd=1, bg="SystemButtonFace")
    
    def on_flag_click(self, flag_code):
        if self.switching or flag_code == self.current_zone:
            return
            
        self.selected_flag = flag_code
        self.highlight_flag(flag_code)
        
        # 开始切换区域
        self.switch_region(flag_code)
    
    def switch_region(self, flag_code):
        global proxy_state
        self.switching = True
        
        # 检查当前VPN连接状态
        self.was_vpn_on = (proxy_state == 1)
        
        # 如果VPN正在运行，先关闭它
        if self.was_vpn_on:
            try:
                # 关闭系统代理
                subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                # 关闭xray进程
                try:
                    subprocess.run(["taskkill", "/f", "/im", "xray.exe"], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    print("xray进程已关闭")
                except subprocess.CalledProcessError:
                    print("xray进程可能未运行或已关闭")
                
                print("VPN和xray已关闭，准备换区")
            except Exception as e:
                print(f"关闭VPN时发生错误: {e}")
        
        # 重置最大进度值并显示进度
        self.max_progress = 0
        self._update_progress_display(get_message("switching_region"))
        
        # 强制刷新UI，确保进度条显示
        self.force_ui_refresh()
        
        # 禁用所有按钮
        for btn in self.flag_buttons.values():
            for child in btn.winfo_children():
                child.config(state="disabled")
        
        # 给UI额外时间渲染，然后启动切换线程（增加延迟确保打包后的exe能正确渲染进度条）
        self.after(200, lambda: self._start_switch_thread(flag_code))
    
    def _start_switch_thread(self, flag_code):
        """延迟启动切换线程，确保UI已渲染"""
        thread = threading.Thread(target=self._switch_region_thread, args=(flag_code,))
        thread.daemon = True
        thread.start()
    
    def _switch_region_thread(self, flag_code):
        """分阶段处理切换请求：初始请求 + 轮询状态"""
        max_retries = 2
        initial_timeout = 30  # 初始请求超时（避免nginx 60秒限制）
        
        for attempt in range(max_retries):
            try:
                print(f"发起切换请求... (尝试 {attempt + 1}/{max_retries})")
                
                # 第一阶段：发起切换请求
                response = requests.post(
                    "https://vvv.xiexievpn.com/switch",
                    json={"code": self.uuid, "newZone": flag_code},
                    headers={"Content-Type": "application/json"},
                    timeout=initial_timeout
                )
                
                if response.status_code == 200:
                    # 切换成功，等待配置更新
                    self._wait_for_config_update()
                    self.after(0, self._on_switch_success, flag_code)
                    return
                elif response.status_code == 202:
                    # 服务器正在处理，进入轮询模式
                    print("服务器正在处理请求，进入轮询模式...")
                    if self._poll_switch_status(flag_code):
                        return  # 成功
                    else:
                        # 轮询失败，尝试重试或报告错误
                        if attempt < max_retries - 1:
                            print("轮询超时，正在重试...")
                            time.sleep(5)
                            continue
                        else:
                            self.after(0, self._on_switch_failed, "切换超时，请检查网络连接")
                            return
                elif response.status_code == 504:
                    # 网关超时，但操作可能仍在进行，直接进入轮询
                    print("网关超时，但操作可能仍在进行，进入轮询模式...")
                    if self._poll_switch_status(flag_code):
                        return  # 成功
                    else:
                        if attempt < max_retries - 1:
                            print("轮询后仍未成功，正在重试...")
                            time.sleep(5)
                            continue
                        else:
                            self.after(0, self._on_switch_failed, "切换超时，请稍后重试")
                            return
                else:
                    # 其他HTTP错误
                    if attempt < max_retries - 1:
                        print(f"切换失败 (HTTP {response.status_code})，正在重试...")
                        time.sleep(3)
                        continue
                    else:
                        self.after(0, self._on_switch_failed, f"HTTP {response.status_code}")
                        return
                        
            except requests.Timeout:
                # 初始请求超时，进入轮询模式看是否操作已开始
                print("初始请求超时，尝试轮询检查状态...")
                if self._poll_switch_status(flag_code):
                    return  # 成功
                else:
                    if attempt < max_retries - 1:
                        print("轮询后未检测到变化，正在重试...")
                        time.sleep(3)
                        continue
                    else:
                        self.after(0, self._on_switch_failed, "请求超时，请检查网络连接")
                        return
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"发生错误: {e}，正在重试...")
                    time.sleep(3)
                    continue
                else:
                    self.after(0, self._on_switch_failed, str(e))
                    return
    
    def _poll_switch_status(self, flag_code):
        """轮询切换状态，使用非阻塞方式"""
        self.poll_attempts = 0
        self.max_poll_attempts = 120  # 120次 * 5秒 = 10分钟
        self.poll_interval = 5000  # 5秒间隔（毫秒）
        self.target_flag_code = flag_code
        
        print(f"开始轮询切换状态，目标区域: {flag_code}")
        self._do_poll_attempt()
        return True
    
    def _do_poll_attempt(self):
        """执行单次轮询尝试（非阻塞）"""
        try:
            # 获取当前用户信息
            response = requests.post(
                "https://vvv.xiexievpn.com/getuserinfo",
                json={"code": self.uuid},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                current_zone = data.get("zone", "")
                vmname = data.get("vmname", "")
                v2rayurl = data.get("v2rayurl", "")

                # 更新UI显示当前状态
                if current_zone and current_zone in REGION_TO_FLAG:
                    display_region = REGION_TO_FLAG[current_zone]
                    self._update_main_window_region(display_region, current_zone)

                # 检查是否切换完成
                target_zone = FLAG_TO_REGION.get(self.target_flag_code, self.target_flag_code)

                # 方法1：检查zone是否已更新到目标区域
                if current_zone == target_zone:
                    print(f"检测到zone已更新到: {current_zone}")
                    if v2rayurl:
                        print(f"v2rayurl也已更新，切换完成")
                        parse_and_write_config(v2rayurl)
                        self.max_progress = 100  # 确保成功时达到100%
                        self._update_progress_display(get_message("switch_success"))
                        self.after(1000, lambda: self._on_switch_success(self.target_flag_code))
                        return
                    else:
                        print("zone已更新但v2rayurl未更新，继续等待...")
                
                # 方法2：检查vmname中是否包含目标标识
                elif vmname and self.target_flag_code in vmname:
                    print(f"检测到vmname包含目标区域: {vmname}")
                    
                    # 如果有vmname，尝试调用createvmloading获取进度
                    try:
                        progress_response = requests.post(
                            "https://vvv.xiexievpn.com/createvmloading",
                            json={"vmname": vmname},
                            headers={"Content-Type": "application/json"},
                            timeout=10
                        )
                        
                        if progress_response.status_code == 200:
                            progress_data = progress_response.json()
                            progress_value = progress_data.get("progress", 0)
                            
                            if isinstance(progress_value, (int, float)) and 0 <= progress_value <= 100:
                                # 只有当新进度大于当前最大进度时才更新
                                if progress_value > self.max_progress:
                                    self.max_progress = progress_value
                                    self._update_progress_display(f"{get_message('processing')}{self.max_progress}%")
                                    print(f"VM创建进度: {self.max_progress}%")
                    except Exception as progress_error:
                        print(f"获取进度时出错: {progress_error}")
                    
                    # 检查v2rayurl是否可用
                    if v2rayurl:
                        print("v2rayurl已可用，切换完成")
                        parse_and_write_config(v2rayurl)
                        self.max_progress = 100  # 确保成功时达到100%
                        self._update_progress_display(get_message("switch_success"))
                        self.after(1000, lambda: self._on_switch_success(self.target_flag_code))
                        return
                    else:
                        print("vmname匹配但v2rayurl未更新，继续等待...")
                
                # 显示轮询进度（每10次显示一次，避免日志过多）
                if self.poll_attempts % 10 == 0:
                    elapsed_minutes = (self.poll_attempts * self.poll_interval // 1000) // 60
                    estimated_progress = min(10 + self.poll_attempts, 90)
                    # 只有当估计进度大于当前最大进度时才更新
                    if estimated_progress > self.max_progress:
                        self.max_progress = estimated_progress
                        progress_text = f"{get_message('processing')}{self.max_progress}%"
                        self._update_progress_display(progress_text)
                    print(f"等待切换完成... (已等待 {elapsed_minutes} 分钟，当前区域: {current_zone})")
                
        except Exception as e:
            print(f"轮询状态时出错: {e}")
        
        # 继续下一次轮询
        self.poll_attempts += 1
        
        if self.poll_attempts < self.max_poll_attempts:
            self.after(self.poll_interval, self._do_poll_attempt)
        else:
            print(f"轮询超时（{self.max_poll_attempts * self.poll_interval // 1000 // 60} 分钟），切换可能失败")
            self._on_switch_failed("切换超时，请检查网络连接")
    
    def _update_progress_display(self, text):
        """更新标题标签显示进度"""
        try:
            if text == get_message("switch_success"):
                # 恢复原标题文本和颜色
                self.title_label.config(text=get_message("select_region"), fg="black")
            else:
                # 显示进度，使用更醒目的红色
                self.title_label.config(text=text, fg="red")
        except Exception as e:
            print(f"更新进度显示时发生错误: {e}")
    
    def _wait_for_config_update(self):
        # 轮询获取新配置 - 参考test.html的逻辑
        max_attempts = 200  # 增加到200次（3秒*200=10分钟）
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    "https://vvv.xiexievpn.com/getuserinfo",
                    json={"code": self.uuid},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()

                    # 实时更新当前区域显示
                    zone = data.get("zone", "")
                    if zone and zone in REGION_TO_FLAG:
                        new_region = REGION_TO_FLAG[zone]
                        self.after(0, self._update_main_window_region, new_region, zone)
                    elif zone:
                        self.after(0, self._update_main_window_region, zone, zone)

                    # 首先检查vmname（参考test.html的pollForVmName逻辑）
                    vmname = data.get("vmname", "")
                    if vmname and self.selected_flag in vmname:
                        print(f"检测到新vmname: {vmname}")

                    # 然后检查v2rayurl
                    v2rayurl = data.get("v2rayurl", "")
                    if v2rayurl:
                        # 解析并更新配置
                        parse_and_write_config(v2rayurl)
                        return
                        
            except Exception as e:
                print(f"Config update attempt {attempt + 1} failed: {e}")
            
            # 每10次显示一次进度（避免日志过多）
            if attempt % 10 == 0:
                print(f"等待配置更新... ({attempt}/{max_attempts})")
            
            time.sleep(3)  # 改为3秒，与test.html保持一致
    
    def _update_main_window_region(self, flag_code, zone):
        """更新主窗口的区域显示"""
        global current_region
        current_region = flag_code
        
        # 直接更新主窗口的区域显示
        try:
            if 'region_label' in globals() and region_label and region_label.winfo_exists():
                region_text = f"{get_message('current_region')}: {get_message(f'region_{flag_code}')}"
                region_label.config(text=region_text)
        except Exception as e:
            print(f"更新区域显示时发生错误: {e}")
    
    def _on_switch_success(self, flag_code):
        global current_region, proxy_state, btn_general_proxy, btn_close_proxy
        current_region = flag_code
        self.current_zone = flag_code
        
        self._update_progress_display(get_message("switch_success"))
        
        # 更新主窗口的区域显示
        update_region_display()
        
        # 如果之前VPN是开启的，重新开启VPN
        if hasattr(self, 'was_vpn_on') and self.was_vpn_on:
            try:
                subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                proxy_state = 1
                if 'btn_general_proxy' in globals() and btn_general_proxy:
                    btn_general_proxy.config(state="disabled")
                if 'btn_close_proxy' in globals() and btn_close_proxy:
                    btn_close_proxy.config(state="normal")
                print("VPN已自动重新开启")
            except Exception as e:
                print(f"自动重新开启VPN时发生错误: {e}")
        
        # 2秒后关闭窗口
        self.after(2000, self.close_window)
    
    def _on_switch_failed(self, error_msg):
        # 恢复原标题标签文本和颜色
        self.title_label.config(text=get_message("select_region"), fg="black")
        
        # 恢复按钮状态
        for btn in self.flag_buttons.values():
            for child in btn.winfo_children():
                child.config(state="normal")
        
        # 恢复原来的高亮
        self.highlight_flag(self.current_zone)
        self.switching = False
        
        messagebox.showerror("Error", f"{get_message('switch_failed')}: {error_msg}")
    
    def close_window(self):
        self.grab_release()
        self.destroy()

def open_region_selector(uuid):
    """打开区域选择器"""
    global current_region
    RegionSelector(window, current_region, uuid)

def update_region_display():
    """更新区域显示"""
    global region_label, current_region
    try:
        if 'region_label' in globals() and region_label and region_label.winfo_exists():
            if current_region:
                region_text = f"{get_message('current_region')}: {get_message(f'region_{current_region}')}"
                region_label.config(text=region_text)
            else:
                # 显示加载状态
                region_text = f"{get_message('current_region')}: {get_message('region_loading')}"
                region_label.config(text=region_text)
    except Exception as e:
        print(f"Error updating region display: {e}")

def force_window_refresh():
    """强制刷新主窗口"""
    global window
    if 'window' in globals() and window:
        window.update_idletasks()
        window.update()
        # Windows特定：使用after延迟确保渲染
        if sys.platform == 'win32':
            window.after(1, lambda: window.update())

def toggle_autostart():
    global proxy_state
    try:
        save_autostart_state(chk_autostart.get())
        exe_path = sys.executable
        arg1 = "1"
        tr_value = f"\"{exe_path}\" {arg1}"
        cmd = [
                "schtasks",
                "/Create",
                "/SC", "ONLOGON",
                "/TN", "simplevpn",
                "/TR", tr_value,
                "/RL", "HIGHEST",
                "/F",
        ]
        try:
             result = subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.CalledProcessError as e:
               print(e.stderr)
        if chk_autostart.get():
            subprocess.run(['schtasks', '/Change', '/TN', 'simplevpn', '/ENABLE'], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.run(['schtasks', '/Change', '/TN', 'simplevpn', '/DISABLE'], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"{get_message('failed_autostart')}: {e.stderr}\nReturn code: {e.returncode}")

def on_chk_change(*args):
    toggle_autostart()

def set_general_proxy():
    global proxy_state, config_ready
    
    # 检查配置文件是否已准备好
    if not config_ready and not os.path.exists(resource_path("config.json")):
        messagebox.showinfo(get_text("app_title"), get_message("config_preparing"))
        return
    
    try:
        subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Information", get_message("vpn_setup_success"))
        btn_general_proxy.config(state="disabled")
        btn_close_proxy.config(state="normal")
        proxy_state = 1
        toggle_autostart()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"{get_message('failed_proxy')}: {e.stderr}")

def close_proxy():
    global proxy_state
    try:
        subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("Information", get_message("vpn_closed"))
        btn_close_proxy.config(state="disabled")
        btn_general_proxy.config(state="normal")
        proxy_state = 0
        toggle_autostart()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"{get_message('failed_close')}: {e.stderr}")

def on_closing():
    close_state = btn_close_proxy["state"]
    general_state = btn_general_proxy["state"]
    if close_state == "normal":
        if general_state == "disabled":
            try:
                subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                messagebox.showinfo("Information", get_message("vpn_temp_closed"))
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"{get_message('failed_exit')}: {e.stderr}")
    window.destroy()

def save_uuid(uuid):
    with open(get_persistent_path("uuid.txt"), "w", encoding="utf-8") as f:
        f.write(uuid)

def load_uuid():
    path_ = get_persistent_path("uuid.txt")
    if os.path.exists(path_):
        with open(path_, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def remove_uuid_file():
    path_ = get_persistent_path("uuid.txt")
    if os.path.exists(path_):
        os.remove(path_)

def check_login():
    entered_uuid = entry_uuid.get().strip()
    try:
        response = requests.post("https://vvv.xiexievpn.com/login", json={"code": entered_uuid})
        if response.status_code == 200:
            if chk_remember.get():
                save_uuid(entered_uuid)
            login_window.destroy()
            show_main_window(entered_uuid)
        else:
            remove_uuid_file()
            if response.status_code == 401:
                messagebox.showerror("Error", get_message("invalid_code"))
            elif response.status_code == 403:
                messagebox.showerror("Error", get_message("expired"))
            else:
                messagebox.showerror("Error", get_message("server_error"))
    except requests.exceptions.RequestException as e:
        remove_uuid_file()
        messagebox.showerror("Error", f"{get_message('connection_error')}: {e}")

def on_remember_changed(*args):
    if not chk_remember.get():
        remove_uuid_file()

def do_adduser(uuid):
    try:
        requests.post(
            "https://vvv.xiexievpn.com/adduser",
            json={"code": uuid},
            timeout=2
        )
    except requests.exceptions.RequestException as e:
        print(f"{get_message('adduser_error')}{e}")

def poll_getuserinfo(uuid):
    global current_region
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

        # 统一更新区域显示（与fetch_config_data逻辑一致）
        if zone and zone in REGION_TO_FLAG:
            current_region = REGION_TO_FLAG[zone]
        elif zone:
            current_region = zone

        # 更新主窗口显示
        update_region_display()

        if v2rayurl:
            parse_and_write_config(v2rayurl)
            return
        else:
            window.after(3000, lambda: poll_getuserinfo(uuid))

    except requests.exceptions.RequestException as e:
        window.after(3000, lambda: poll_getuserinfo(uuid))

def parse_and_write_config(url_string):
    """
    解析 VLESS URL 并生成 Xray 配置文件 (已修复 True/False 语法)
    """
    try:
        if not url_string.startswith("vless://"):
            return

        # 格式: vless://uuid@IP:PORT?param=val#tag
        # 分离参数部分
        if "?" in url_string:
            main_part = url_string.split("?")[0]
            params_part = url_string.split("?")[1].split("#")[0]
        else:
            main_part = url_string.split("#")[0]
            params_part = ""
        
        after_proto = main_part.split("://")[1]
        uuid = after_proto.split("@")[0]
        host_port = after_proto.split("@")[1]
        domain = host_port.split(":")[0] 
        jsonport = int(host_port.split(":")[1])

        params = urllib.parse.parse_qs(params_part)

        public_key = params.get('pbk', [''])[0]
        short_id = params.get('sid', [''])[0]
        sni = params.get('sni', ['getsteamcard.com'])[0]
        fp = params.get('fp', ['chrome'])[0]
        flow = params.get('flow', ['xtls-rprx-vision'])[0]

        if not public_key:
            public_key = "mUzqKeHBc-s1m03iD8Dh1JoL2B9JwG5mMbimEoJ523o"

        # 构建 routing 规则
        routing_rules = [
            {"type": "field", "domain": ["geosite:category-ads-all"], "outboundTag": "block"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "block"},
            {"type": "field", "network": "udp", "port": 443, "outboundTag": "block"},
            {"type": "field", "domain": ["geosite:cn", "geosite:category-games@cn"], "outboundTag": "direct"},
            {"type": "field", "ip": ["geoip:cn", "geoip:private"], "outboundTag": "direct"},
            {"type": "field", "port": "0-65535", "outboundTag": "proxy"}
        ]

        outbounds = [
            {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": domain,
                            "port": jsonport,
                            "users": [
                                {
                                    "id": uuid,
                                    "encryption": "none",
                                    "flow": flow 
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
                        "fingerprint": fp,
                        "serverName": sni,
                        "publicKey": public_key,
                        "shortId": short_id,
                        "spiderX": ""
                    },
                    "sockopt": {
                        "tcpNoDelay": True, 
                        "tcpKeepAliveIdle": 100
                    }
                }
            },
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"}
        ]

        config_data = {
            "log": {"loglevel": "none", "error": ""},
            "dns": {
                "servers": [
                    {
                        "tag": "dns_proxy",
                        "address": "https://1.1.1.1/dns-query",
                        "domains": ["geosite:geolocation-!cn"],
                        "detour": "proxy"
                    },
                    {
                        "tag": "dns_direct",
                        "address": "223.5.5.5",
                        "domains": ["geosite:cn", "geosite:category-games@cn"],
                        "detour": "direct"
                    }
                ],
                "queryStrategy": "UseIPv4"
            },
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": routing_rules
            },
            "inbounds": [
                {
                    "tag": "socks",
                    "port": 10808,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"],
                        "routeOnly": False
                    },
                    "settings": {"udp": True}
                },
                {
                    "tag": "http",
                    "port": 1080,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"],
                        "routeOnly": False
                    }
                }
            ],
            "outbounds": outbounds
        }

        with open(resource_path("config.json"), "w", encoding="utf-8") as config_file:
            json.dump(config_data, config_file, indent=4)
        
        global config_ready, pending_autostart
        config_ready = True
        
        if pending_autostart:
            pending_autostart = False
            set_general_proxy()
        
        if 'btn_general_proxy' in globals() and btn_general_proxy is not None:
            btn_general_proxy.config(state="normal")
            
        print(get_message("config_written"))

    except Exception as e:
        print(f"Config parse error: {e}")
        try:
            messagebox.showerror("Error", f"{get_message('config_error')}: {e}")
        except:
            pass

def fetch_config_data(uuid):
    global current_region
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

        # 更新当前区域
        if zone and zone in REGION_TO_FLAG:
            current_region = REGION_TO_FLAG[zone]
        elif zone:
            current_region = zone

        # 更新主窗口显示
        update_region_display()

        public_key = response_data.get("publicKey", "")
        short_id = response_data.get("shortId", "")

        if not v2rayurl and not zone:
            print(get_message("waiting_config"))
            do_adduser(uuid)
            window.after(10, lambda: poll_getuserinfo(uuid))

        elif not v2rayurl:
            window.after(10, lambda: poll_getuserinfo(uuid))

        else:
            parse_and_write_config(v2rayurl)
            if public_key and short_id:
                print(get_message("user_config_updated"))

    except requests.exceptions.RequestException as e:
        print(f"{get_message('connection_error')}: {e}")
        messagebox.showerror("Error", f"{get_message('connection_error')}: {e}")

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
    
    # 初始状态：如果配置未准备好，禁用开启VPN按钮
    if not config_ready and not os.path.exists(resource_path("config.json")):
        btn_general_proxy.config(state="disabled")
    
    btn_general_proxy.pack(pady=10)
    btn_close_proxy.pack(pady=10)

    chk_autostart = tk.BooleanVar()
    chk_autostart.set(load_autostart_state())
    chk_autostart.trace_add("write", on_chk_change)

    chk_autostart_button = tk.Checkbutton(window, text=get_text("autostart"), variable=chk_autostart, command=toggle_autostart)
    chk_autostart_button.pack(pady=10)

    # 添加区域切换按钮
    btn_switch_region = tk.Button(window, text=get_text("switch_region"), command=lambda: open_region_selector(uuid))
    btn_switch_region.pack(pady=10)
    
    # 显示当前区域
    region_label = tk.Label(window, text="", font=("Arial", 9), fg="gray")
    region_label.pack(pady=5)

    fetch_config_data(uuid)
    
    # 首次更新区域显示
    window.after(1000, update_region_display)

    # 检查更新（延迟3秒，让界面先加载完成）
    def check_update_async():
        def update_check():
            update_info = check_for_updates()
            if update_info:
                window.after(0, lambda: show_update_dialog(update_info))
        threading.Thread(target=update_check, daemon=True).start()

    window.after(3000, check_update_async)

    if len(sys.argv) > 1:
        try:
            start_state = int(sys.argv[1])
            if start_state == 1:
                global pending_autostart
                if config_ready:
                    set_general_proxy()
                else:
                    pending_autostart = True  # 等待配置准备完成后自动启动
        except ValueError:
            pass

    window.deiconify()
    window.attributes('-topmost', True)
    window.attributes('-topmost', False)     

    window.mainloop()

login_window = tk.Tk()
login_window.title(get_text("login_title"))
login_window.geometry("300x200")
login_window.iconbitmap(resource_path("favicon.ico"))

label_uuid = tk.Label(login_window, text=get_text("login_prompt"))
label_uuid.pack(pady=10)

entry_uuid = tk.Entry(login_window)
entry_uuid.pack(pady=5)
entry_uuid.bind("<Control-Key-a>", lambda event: entry_uuid.select_range(0, tk.END))
entry_uuid.bind("<Control-Key-c>", lambda event: login_window.clipboard_append(entry_uuid.selection_get()))
entry_uuid.bind("<Control-Key-v>", lambda event: entry_uuid.insert(tk.INSERT, login_window.clipboard_get()))

menu = Menu(entry_uuid, tearoff=0)
menu.add_command(label=get_text("copy"), command=lambda: login_window.clipboard_append(entry_uuid.selection_get()))
menu.add_command(label=get_text("paste"), command=lambda: entry_uuid.insert(tk.INSERT, login_window.clipboard_get()))
menu.add_command(label=get_text("select_all"), command=lambda: entry_uuid.select_range(0, tk.END))

def show_context_menu(event):
    menu.post(event.x_root, event.y_root)

entry_uuid.bind("<Button-3>", show_context_menu)

chk_remember = tk.BooleanVar()
chk_remember_button = tk.Checkbutton(login_window, text=get_text("auto_login"), variable=chk_remember)
chk_remember_button.pack(pady=5)

chk_remember.trace_add("write", on_remember_changed)

btn_login = tk.Button(login_window, text=get_text("login_button"), command=check_login)
btn_login.pack(pady=10)

saved_uuid = load_uuid()
if saved_uuid:
    entry_uuid.insert(0, saved_uuid)
    check_login()

login_window.mainloop()
