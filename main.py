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
import base64
import socket
import concurrent.futures
import random
import socks                
import urllib3.contrib.socks

CURRENT_VERSION = "3.1.0"
SUB_DOMAIN = "sub.xiexievpn.com"

proxy_state = 0
is_manual_switching = False
pending_autostart = False
current_region = None
current_uuid = None
current_protocol = None
window = None
config_ready = False
protocol_label = None
penalized_protocol = None
penalty_until = 0
current_node_url = None

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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

    if "protocol_label" not in lang_data:
        lang_data["protocol_label"] = "Protocol"
    if "protocol_auto" not in lang_data:
        lang_data["protocol_auto"] = "Auto"
    msgs = lang_data.get("messages", {})
    if "speed_testing" not in msgs:
        msgs["speed_testing"] = "Speed testing..."
    if "speed_test_failed" not in msgs:
        msgs["speed_test_failed"] = "Speed test failed"
    if "degrading" not in msgs:
        msgs["degrading"] = "Network blocked, smart fallback..."
    lang_data["messages"] = msgs

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

def test_tcp_ping(host, port):
    try:
        st = time.time()
        with socket.create_connection((host, int(port)), timeout=3):
            return (time.time() - st) * 1000
    except Exception:
        return float('inf')

def generate_singbox_config(proxy_outbound):
    control_plane_domains = [
        "vvv.xiexievpn.com",
        "sub.xiexievpn.com",
        "xiexievpn.com"
    ]
    config_data = {
        "log": {"level": "error"},
        "dns": {
            "servers": [
                {"tag": "dns-remote", "address": "https://1.1.1.1/dns-query", "address_resolver": "dns-local", "detour": "proxy"},
                {"tag": "dns-local", "address": "223.5.5.5", "detour": "direct"}
            ],
            "rules": [
                {"outbound": "any", "server": "dns-local"},
                {"domain_suffix": control_plane_domains, "server": "dns-local"},
                {"rule_set": ["geosite-cn"], "server": "dns-local"}
            ],
            "final": "dns-remote",
            "strategy": "ipv4_only"
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "xiexievpn",
                "address": ["198.18.0.1/30"],
                "auto_route": True,
                "strict_route": True,
                "stack": "mixed",
                "sniff": True,
                "sniff_override_destination": True
            },
            {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 10808},
            {"type": "mixed", "tag": "mixed-in2", "listen": "127.0.0.1", "listen_port": 1080}
        ],
        "outbounds": [
            proxy_outbound,
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
            {"type": "dns", "tag": "dns-out"}
        ],
        "route": {
            "rule_set": [
                {"tag": "geoip-cn", "type": "local", "format": "binary", "path": os.path.abspath(resource_path("geoip-cn.srs")).replace("\\", "/")},
                {"tag": "geosite-cn", "type": "local", "format": "binary", "path": os.path.abspath(resource_path("geosite-cn.srs")).replace("\\", "/")}
            ],
            "rules": [
                {"protocol": "dns", "outbound": "dns-out"},
                {"port": 53, "outbound": "dns-out"},
                {"domain_suffix": control_plane_domains, "outbound": "direct"},
                {"protocol": "bittorrent", "outbound": "direct"},
                {"ip_is_private": True, "outbound": "direct"},
                {"rule_set": ["geoip-cn", "geosite-cn"], "outbound": "direct"}
            ],
            "auto_detect_interface": True,
            "final": "proxy"
        }
    }
    with open(resource_path("config.json"), "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    return True

def test_hy2_url_test(node):
    temp_port = random.randint(30000, 39999)
    config = {
        "log": {"level": "fatal"},
        "inbounds": [{"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": temp_port}],
        "outbounds": [{
            "type": "hysteria2", "tag": "proxy", "server": node["host"], "server_port": node["port"],
            "password": node.get("uuid", ""), "tls": {"enabled": True, "server_name": node.get("sni", node["host"]), "insecure": False}
        }]
    }
    config_path = os.path.join(tempfile.gettempdir(), f"hy2_test_{temp_port}.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    proc = None
    try:
        proc = subprocess.Popen(
            [resource_path("sing-box.exe"), "run", "-c", config_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(2)
        if proc.poll() is not None:
            return float('inf')

        proxies = {'http': f'socks5h://127.0.0.1:{temp_port}',
                   'https': f'socks5h://127.0.0.1:{temp_port}'}
        st = time.time()
        resp = requests.get("http://cp.cloudflare.com/generate_204",
                           proxies=proxies, timeout=5)
        if resp.status_code == 204:
            return (time.time() - st) * 1000
        return float('inf')
    except Exception:
        return float('inf')
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                pass
        try:
            os.remove(config_path)
        except Exception:
            pass

def extract_subscription_links(links_text):
    normalized_text = links_text or ""

    if "://" not in normalized_text:
        try:
            pad = len(normalized_text) % 4
            if pad:
                normalized_text += "=" * (4 - pad)
            normalized_text = base64.b64decode(normalized_text).decode("utf-8")
        except Exception:
            pass

    links = []
    for line in normalized_text.strip().splitlines():
        line = line.strip()
        if line.startswith("vless://") or line.startswith("hysteria2://") or line.startswith("hy2://"):
            links.append(line)
    return links

def get_single_vless_link(links_text):
    links = extract_subscription_links(links_text)
    if len(links) == 1 and links[0].startswith("vless://"):
        return links[0]
    return None

def extract_region_from_link(link):
    try:
        if "#" not in link:
            return None
        frag = urllib.parse.unquote(link.split("#", 1)[1]).strip().lower()
        if not frag:
            return None

        if frag.endswith("-hy2"):
            frag = frag[:-4]

        if frag in FLAG_TO_REGION:
            return frag

        if frag in REGION_TO_FLAG:
            return REGION_TO_FLAG[frag]

        for aws_region, flag_code in REGION_TO_FLAG.items():
            if frag.startswith(aws_region):
                return flag_code

        return None
    except Exception:
        return None

def speed_test_nodes(links_text):
    nodes = []

    for line in extract_subscription_links(links_text):
        try:
            protocol = "vless" if line.startswith("vless") else "hy2"
            main_part = line.split("://")[1]
            host_port = main_part.split("@")[1].split("?")[0].split("/")[0]
            host_parts = host_port.split(":")
            host = host_parts[0]
            port = int(host_parts[1]) if len(host_parts) > 1 else 443
            node_info = {"protocol": protocol, "url": line, "host": host, "port": port}
            if protocol == "hy2":
                node_info["uuid"] = main_part.split("@")[0]
                query_part = main_part.split("?")[1].split("#")[0] if "?" in main_part else ""
                node_info["sni"] = urllib.parse.parse_qs(query_part).get('sni', [host])[0]
            nodes.append(node_info)
        except:
            pass
            
    if not nodes:
        return None

    def test_node(node):
        if node["protocol"] == "hy2":
            node["ping"] = test_hy2_url_test(node)
        else:
            tcp_ping = test_tcp_ping(node["host"], node["port"])
            node["ping"] = tcp_ping * 3 + 100 if tcp_ping != float('inf') else float('inf')
        if penalized_protocol == node["protocol"] and time.time() < penalty_until:
            if node["ping"] != float('inf'):
                node["ping"] += 5000
        return node
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, max(1, len(nodes)))) as executor:
        results = list(executor.map(test_node, nodes))
        
    valid = [r for r in results if r["ping"] != float('inf')]
    if not valid:
        nodes[0]["ping"] = float('inf')
        return nodes[0]
        
    valid.sort(key=lambda x: x["ping"])
    best = valid[0]
    
    for n in valid:
        if n["protocol"] == "hy2" and n["ping"] - best["ping"] <= 50:
            best = n
            break
    return best

def write_vless_config(url_string):
    try:
        if not url_string.startswith("vless://"):
            return False
        uuid = url_string.split("@")[0].split("://")[1]
        main_part = url_string.split("@")[1]
        domain_port_part = main_part.split("?")[0]
        host = domain_port_part.split(":")[0]
        port = int(domain_port_part.split(":")[1]) if ":" in domain_port_part else 443

        domain = host.split(".")[0]
        query_part = url_string.split("?")[1].split("#")[0] if "?" in main_part else ""
        params = urllib.parse.parse_qs(query_part)

        sni = params.get('sni', [f"{domain}.rocketchats.xyz"])[0].replace("www.", "")
        public_key = params.get('pbk', [''])[0] or "mUzqKeHBc-s1m03iD8Dh1JoL2B9JwG5mMbimEoJ523o"
        short_id = params.get('sid', [''])[0]

        proxy_outbound = {
            "type": "vless", "tag": "proxy", "server": host, "server_port": port, "uuid": uuid, "flow": "xtls-rprx-vision",
            "tls": {
                "enabled": True, "server_name": sni,
                "utls": {"enabled": True, "fingerprint": "chrome"},
                "reality": {"enabled": True, "public_key": public_key, "short_id": short_id}
            },
            "packet_encoding": "xudp"
        }
        return generate_singbox_config(proxy_outbound)
    except Exception:
        return False

def write_hy2_config(url_string):
    try:
        main_part = url_string.split("://")[1]
        uuid = main_part.split("@")[0]
        host_port = main_part.split("@")[1].split("?")[0].split("/")[0]
        host = host_port.split(":")[0]
        port = int(host_port.split(":")[1]) if ":" in host_port else 443
        query_part = main_part.split("?")[1].split("#")[0] if "?" in main_part else ""
        sni = urllib.parse.parse_qs(query_part).get('sni', [host])[0]

        proxy_outbound = {
            "type": "hysteria2", "tag": "proxy", "server": host, "server_port": port, "password": uuid,
            "tls": {"enabled": True, "server_name": sni, "insecure": False}
        }
        return generate_singbox_config(proxy_outbound)
    except Exception:
        return False

def parse_and_write_config_async(links_text, callback=None, skip_speed_test=False):
    global current_protocol, config_ready, pending_autostart
    
    if not skip_speed_test and 'protocol_label' in globals() and protocol_label and window:
        window.after(0, lambda: protocol_label.config(text=get_message("speed_testing"), fg="orange"))
        
    def task():
        global current_protocol, config_ready, pending_autostart, current_node_url, current_region
        if skip_speed_test:
            single_vless_link = get_single_vless_link(links_text)
            if single_vless_link:
                best_node = {"protocol": "vless", "url": single_vless_link, "ping": float('inf')}
            else:
                best_node = None
        else:
            best_node = speed_test_nodes(links_text)
        if not best_node:
            if 'protocol_label' in globals() and protocol_label and window:
                window.after(0, lambda: protocol_label.config(text=get_message("speed_test_failed"), fg="red"))
            if callback and window:
                window.after(0, lambda: callback(False))
            return

        if best_node["url"] == current_node_url and config_ready:
            if callback and window:
                window.after(0, lambda: callback(True))
            return
            
        if best_node["protocol"] == "vless":
            success = write_vless_config(best_node["url"])
        else:
            success = write_hy2_config(best_node["url"])
            
        if success:
            current_protocol = best_node["protocol"]
            config_ready = True
            current_node_url = best_node["url"]
            selected_region = extract_region_from_link(best_node["url"])
            if selected_region:
                current_region = selected_region
            
            def update_ui():
                global pending_autostart
                if 'protocol_label' in globals() and protocol_label:
                    p_text = "VLESS ⚡" if current_protocol == "vless" else "HY2 🚀"
                    ping_text = f"{int(best_node['ping'])}ms" if best_node['ping'] != float('inf') else "Blind"
                    if penalized_protocol and time.time() < penalty_until and current_protocol != penalized_protocol:
                        p_text += " (↓ fallback)"
                    protocol_label.config(text=f"{get_text('protocol_label')}: {p_text} ({ping_text})", fg="green")
                update_region_display()
                
                if pending_autostart:
                    pending_autostart = False
                    set_general_proxy(show_success_msg=False)
                elif proxy_state == 1:
                    subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    time.sleep(0.5)
                    subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                elif 'btn_general_proxy' in globals() and btn_general_proxy and proxy_state == 0:
                    btn_general_proxy.config(state="normal")
                
                if callback:
                    callback(True)
                    
            if window:
                window.after(0, update_ui)
        else:
            if callback and window:
                window.after(0, lambda: callback(False))
                
    threading.Thread(target=task, daemon=True).start()

def fetch_subscription(uuid, from_watchdog=False):
    global current_region
    no_proxy = {"http": None, "https": None}
    
    def task():
        global current_region, current_protocol, penalized_protocol, penalty_until
        links_text = ""
        prev_region = current_region
        region_changed = False
        
        try:
            resp = requests.get(f"https://{SUB_DOMAIN}/sub/{uuid}?t={int(time.time())}", timeout=5, proxies=no_proxy)
            if resp.status_code == 200:
                links_text = resp.text.strip()
        except:
            pass
        
        try:
            response = requests.post("https://vvv.xiexievpn.com/getuserinfo",
                                     json={"code": uuid}, proxies=no_proxy, timeout=10)
            if response.status_code == 200:
                data = response.json()
                zone = data.get("zone", "")
                v2rayurl = data.get("v2rayurl", "")
                
                if zone:
                    mapped_region = REGION_TO_FLAG.get(zone, zone)
                    if prev_region and prev_region != mapped_region:
                        region_changed = True
                    current_region = mapped_region
                    if window:
                        window.after(0, update_region_display)
                
                if not links_text and v2rayurl:
                    links_text = v2rayurl
                
                if not v2rayurl and not zone:
                    try:
                        requests.post("https://vvv.xiexievpn.com/adduser",
                                      json={"code": uuid}, timeout=2, proxies=no_proxy)
                    except:
                        pass
                    if window:
                        window.after(3000, lambda: fetch_subscription(uuid))
                    return
                
                if not v2rayurl and zone:
                    if window:
                        window.after(3000, lambda: fetch_subscription(uuid))
                    return
        except:
            pass
            
        if links_text:
            if from_watchdog and get_single_vless_link(links_text):
                penalized_protocol = None
                penalty_until = 0
                parse_and_write_config_async(links_text, skip_speed_test=True)
            else:
                if from_watchdog:
                    if region_changed:
                        penalized_protocol = None
                        penalty_until = 0
                    else:
                        penalized_protocol = current_protocol
                        penalty_until = time.time() + 300
                        if 'protocol_label' in globals() and protocol_label and window:
                            window.after(0, lambda: protocol_label.config(
                                text=get_message("degrading"), fg="red"))
                parse_and_write_config_async(links_text)
            
    threading.Thread(target=task, daemon=True).start()

REGION_TO_FLAG = {
    "us-west-2": "us",
    "ap-northeast-2": "jp",
    "ap-northeast-1": "jj",
    "ap-southeast-1": "si",
    "eu-central-1": "ge",
    "eu-north-1": "sw"
}
FLAG_TO_REGION = {v: k for k, v in REGION_TO_FLAG.items()}
REGIONS = [
    ("jp", "ap-northeast-2"), ("us", "us-west-2"), ("jj", "ap-northeast-1"),
    ("si", "ap-southeast-1"), ("ge", "eu-central-1"), ("sw", "eu-north-1")
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
        self.target_flag_code = None
        
        self.title(get_message("select_region"))
        self.geometry("480x360")
        self.iconbitmap(resource_path("favicon.ico"))
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.title_label = tk.Label(main_frame, text=get_message("select_region"), font=("Arial", 14, "bold"))
        self.title_label.pack(pady=(0, 15))

        self.current_label = tk.Label(main_frame, font=("Arial", 10), fg="blue")
        self.current_label.pack(pady=(0, 10))
        
        txt = f"{get_message('current_region')}: {get_message(f'region_{current_zone}')}" if current_zone else f"{get_message('current_region')}: {get_message('region_loading')}"
        self.current_label.config(text=txt)

        self.create_flag_grid(main_frame)
    
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
            except Exception:
                pass
    
    def highlight_flag(self, flag_code):
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
        self.switch_region(flag_code)
    
    def switch_region(self, flag_code):
        global proxy_state, is_manual_switching
        is_manual_switching = True
        
        self.switching = True
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.was_vpn_on = (proxy_state == 1)

        if self.was_vpn_on:
            try:
                subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    subprocess.run(["taskkill", "/f", "/im", "sing-box.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                except:
                    pass
            except Exception:
                pass

        self.max_progress = 0
        self.target_flag_code = flag_code
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
                    return
                elif response.status_code in [202, 504]:
                    if self._poll_switch_status(flag_code):
                        return
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
        no_proxy = {"http": None, "https": None}
        self.max_progress = 0
        
        for attempt in range(120):
            if not self.switching:
                return False
            try:
                response = requests.post("https://vvv.xiexievpn.com/getuserinfo",
                                         json={"code": self.uuid},
                                         proxies=no_proxy,
                                         timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    current_zone = data.get("zone", "")
                    vmname = data.get("vmname", "")

                    if current_zone and current_zone in REGION_TO_FLAG:
                        self.after(0, lambda z=current_zone: self._update_main_window_region(REGION_TO_FLAG.get(z, z), z))

                    if current_zone == self.target_flag_code and data.get("v2rayurl"):
                        self.after(0, lambda url=data.get("v2rayurl"): self._handle_poll_success(url))
                        return True
                    
                    if not vmname and data.get("v2rayurl") and self.target_flag_code != 'us':
                        self.after(0, lambda url=data.get("v2rayurl"): self._handle_poll_success(url))
                        return True
                    
                    if vmname and self.target_flag_code in vmname:
                        try:
                            p_resp = requests.post("https://vvv.xiexievpn.com/createvmloading",
                                                   json={"vmname": vmname},
                                                   proxies=no_proxy,
                                                   timeout=5)
                            if p_resp.status_code == 200:
                                prog = p_resp.json().get("progress", 0)
                                
                                if prog >= 100:
                                    self.max_progress = 100
                                    self.after(0, lambda: self._update_progress_display(get_message("switch_success")))
                                    time.sleep(3)
                                    continue
                                
                                if prog > self.max_progress:
                                    self.max_progress = prog
                                    self.after(0, lambda p=prog: self._update_progress_display(f"{get_message('processing')}{p}%"))
                        except Exception:
                            pass

                    if attempt % 10 == 0:
                        est_prog = min(10 + attempt, 90)
                        if est_prog > self.max_progress:
                            self.max_progress = est_prog
                            self.after(0, lambda p=est_prog: self._update_progress_display(f"{get_message('processing')}{p}%"))
            except Exception:
                pass

            time.sleep(5)
        
        self.after(0, lambda: self._on_switch_failed("Timeout"))
        return False
    
    def _handle_poll_success(self, v2rayurl):
        self._update_progress_display(get_message("speed_testing"))
        parse_and_write_config_async(v2rayurl, callback=self._on_config_ready)

    def _on_config_ready(self, success):
        if success:
            self.max_progress = 100
            self._update_progress_display(get_message("switch_success"))
            self.after(1000, lambda: self._on_switch_success(self.target_flag_code))
        else:
            self._on_switch_failed("Config generation failed")

    def _update_progress_display(self, text):
        try:
            color = "black" if text == get_message("switch_success") else "red"
            self.title_label.config(text=text, fg=color)
        except:
            pass
    
    def _wait_for_config_update(self):
        no_proxy = {"http": None, "https": None}
        for _ in range(200):
            if not self.switching:
                return
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
                        self.after(0, lambda z=zone: self._update_main_window_region(REGION_TO_FLAG.get(z, z), z))
                    if v2rayurl:
                        self.after(0, lambda url=v2rayurl: self._handle_poll_success(url))
                        return
            except:
                pass
            time.sleep(3)
    
    def _update_main_window_region(self, flag_code, zone):
        global current_region
        current_region = flag_code
        try:
            if 'region_label' in globals() and region_label:
                region_label.config(text=f"{get_message('current_region')}: {get_message(f'region_{flag_code}')}")
        except:
            pass

    def _on_switch_success(self, flag_code):
        global current_region, proxy_state, btn_general_proxy, btn_close_proxy, is_manual_switching, current_protocol, penalized_protocol
        
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        
        current_region = flag_code
        self.current_zone = flag_code
        self._update_progress_display(get_message("switch_success"))
        update_region_display()

        if hasattr(self, 'was_vpn_on') and self.was_vpn_on:
            try:
                subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(0.5)
                subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                proxy_state = 1
                if 'btn_general_proxy' in globals() and btn_general_proxy:
                    btn_general_proxy.config(state="disabled")
                if 'btn_close_proxy' in globals() and btn_close_proxy:
                    btn_close_proxy.config(state="normal")
            except:
                pass
        
        penalized_protocol = None
        is_manual_switching = False
        self.after(2000, self.close_window)
    
    def _on_switch_failed(self, error_msg):
        global is_manual_switching
        self.protocol("WM_DELETE_WINDOW", self.close_window)
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
    except:
        pass

def toggle_autostart():
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

def set_general_proxy(show_success_msg=True):
    global proxy_state, config_ready, current_protocol
    if not config_ready and not os.path.exists(resource_path("config.json")):
        messagebox.showinfo(get_text("app_title"), get_message("config_preparing"))
        return
    try:
        subprocess.run(["cmd", "/c", resource_path("close.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(0.5)
        subprocess.run(["cmd", "/c", resource_path("internet.bat")], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        if show_success_msg:
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
        except:
            pass
    window.destroy()

def check_proxy_connectivity():
    proxies = {'http': 'http://127.0.0.1:1080', 'https': 'http://127.0.0.1:1080'}
    try:
        if requests.get("http://cp.cloudflare.com/generate_204", proxies=proxies, timeout=5).status_code == 204:
            return True
        return False
    except:
        return False

def connection_watchdog_thread(uuid):
    global proxy_state, window, is_manual_switching, current_protocol
    global penalized_protocol, penalty_until
    
    while True:
        time.sleep(10)

        if is_manual_switching:
            continue

        if proxy_state == 1:
            if not check_proxy_connectivity():
                time.sleep(1.5)
                if not check_proxy_connectivity():
                    fetch_subscription(uuid, from_watchdog=True)
                    time.sleep(15)

def show_main_window(uuid):
    global window, btn_general_proxy, btn_close_proxy, chk_autostart, current_uuid, region_label, protocol_label
    current_uuid = uuid
    window = tk.Tk()
    window.title(get_text("app_title"))
    window.geometry("300x360")
    window.iconbitmap(resource_path("favicon.ico"))
    window.protocol("WM_DELETE_WINDOW", on_closing)

    btn_general_proxy = tk.Button(window, text=get_text("open_vpn"), command=lambda: set_general_proxy(show_success_msg=True))
    btn_close_proxy = tk.Button(window, text=get_text("close_vpn"), command=close_proxy)

    if not config_ready and not os.path.exists(resource_path("config.json")):
        btn_general_proxy.config(state="disabled")
    
    btn_close_proxy.config(state="disabled")
    
    btn_general_proxy.pack(pady=10)
    btn_close_proxy.pack(pady=10)

    chk_autostart = tk.BooleanVar()
    chk_autostart.set(load_autostart_state())
    chk_autostart.trace_add("write", on_chk_change)
    tk.Checkbutton(window, text=get_text("autostart"), variable=chk_autostart, command=toggle_autostart).pack(pady=5)

    tk.Button(window, text=get_text("switch_region"), command=lambda: open_region_selector(uuid)).pack(pady=5)
    region_label = tk.Label(window, text="", font=("Arial", 9), fg="gray")
    region_label.pack(pady=2)
    
    protocol_label = tk.Label(window, text=f"{get_text('protocol_label')}: {get_text('protocol_auto')}", font=("Arial", 9, "bold"), fg="gray")
    protocol_label.pack(pady=2)

    fetch_subscription(uuid)
    window.after(1000, update_region_display)

    def check_update_async():
        def update_check():
            update_info = check_for_updates()
            if update_info:
                window.after(0, lambda: show_update_dialog(update_info))
        threading.Thread(target=update_check, daemon=True).start()
        
    window.after(3000, check_update_async)

    monitor_thread = threading.Thread(target=connection_watchdog_thread, args=(uuid,), daemon=True)
    monitor_thread.start()
    
    if len(sys.argv) > 1:
        try:
            if int(sys.argv[1]) == 1:
                global pending_autostart
                if config_ready:
                    set_general_proxy(show_success_msg=False)
                else:
                    pending_autostart = True
        except:
            pass

    window.deiconify()
    window.attributes('-topmost', True)
    window.attributes('-topmost', False)
    window.mainloop()

def on_remember_changed(*args):
    if not chk_remember.get():
        remove_uuid_file()

def check_login():
    entered_uuid = entry_uuid.get().strip()
    no_proxy = {"http": None, "https": None}
    try:
        response = requests.post("https://vvv.xiexievpn.com/login", json={"code": entered_uuid}, proxies=no_proxy, timeout=10)
        if response.status_code == 200:
            if chk_remember.get():
                save_uuid(entered_uuid)
            login_window.destroy()
            show_main_window(entered_uuid)
        else:
            remove_uuid_file()
            msg = get_message("invalid_code") if response.status_code == 401 else get_message("expired") if response.status_code == 403 else get_message("server_error")
            messagebox.showerror("Error", msg)
    except Exception as e:
        remove_uuid_file()
        messagebox.showerror("Error", f"{get_message('connection_error')}: {e}")

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
