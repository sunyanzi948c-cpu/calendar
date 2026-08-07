import customtkinter as ctk
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
import winsound
import socket
import sys
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from tkcalendar import DateEntry
import requests # 【新增】用來與 Google Apps Script 溝通

# ==========================================
# 🚨 請填入你的 Google Apps Script (GAS) API 網址
# ==========================================
GAS_API_URL = "https://script.google.com/macros/s/AKfycbwvYsXf_AQ55AanxcjCfYTzsASRgnqMqZltBxqDY_H8zKZ-aeuRDYaNRnxw0r21sXZd/exec"

# 全域變數，用來在記憶體中暫存任務，方便鬧鐘讀取
global_tasks = []
current_uid = ""

# --- 🚀 視窗置中公用函數 ---
def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    window.geometry(f"{width}x{height}+{x}+{y}")

# --- 🚀 防止重複啟動檢查 ---
_lock_socket = None
def check_single_instance():
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(('127.0.0.1', 65432))
    except socket.error:
        root = ctk.CTk()
        root.withdraw()
        messagebox.showwarning("系統提示", "程式已在執行中，請檢查工作列。")
        sys.exit()

# --- 1. 雲端同步功能 (取代原本的 SQLite) ---
def sync_to_cloud(action, payload):
    """將操作丟給背景執行緒去發送網路請求，避免畫面卡頓"""
    def _sync():
        try:
            data = {"uid": current_uid, "action": action}
            data.update(payload)
            requests.post(GAS_API_URL, json=data)
        except Exception as e:
            print(f"雲端同步失敗: {e}")
    threading.Thread(target=_sync, daemon=True).start()

# --- 2. 鬧鐘監控執行緒 (直接讀取記憶體中的 global_tasks) ---
def alarm_monitor():
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for task in global_tasks:
                match_time = (task.get('time') == now or task.get('time2') == now)
                
                if not task.get('is_completed') and match_time:
                    if not task.get('alarm_triggered', False):
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                        reminder_msg = f"⏱ 任務提醒：\n\n您設定的時間已到。\n────────────────────\n任務：{task['content']}\n────────────────────\n請即時處理。"
                        root = ctk.CTk()
                        root.withdraw()
                        root.attributes("-topmost", True)
                        messagebox.showinfo("⏰ 系統提醒", reminder_msg, parent=root)
                        root.destroy()
                        task['alarm_triggered'] = True
                        time.sleep(61) 
                
                elif task.get('time') != now and task.get('time2') != now:
                    task['alarm_triggered'] = False
                    
        except Exception as e:
            print(f"鬧鐘監控發生錯誤: {e}")
            time.sleep(5)
            
        time.sleep(10)

# --- 3. 彈窗介面 (與原本相同，省略細節以求精簡，請保持你原本的 EditDialog 類別) ---
class EditDialog(ctk.CTkToplevel):
    # ...(這裡完全保留你原本的 EditDialog 程式碼，不需修改)...
    def __init__(self, parent, current_content, current_priority, current_category, current_time, current_time2=""):
        super().__init__(parent)
        self.title("編輯任務詳情")
        center_window(self, 460, 580)
        self.attributes("-topmost", True)
        self.grab_set()
        self.configure(fg_color="#F0F2F5")
        
        self.result = {"content": None, "priority": None, "category": None, "time": None, "time2": None}
        current_time2 = current_time2 or ""
        
        # ... ( UI 元件建立與綁定 ) ...
        # 因篇幅限制，請將原本 EditDialog 裡面的 UI 程式碼直接貼回這裡。
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=30)
        ctk.CTkButton(btn_frame, text="儲存變更", width=130, height=40, fg_color="#4A5568", text_color="white", command=self.on_confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", width=130, height=40, fg_color="#E2E8F0", text_color="#333333", command=self.destroy).pack(side="left", padx=10)

    def on_confirm(self):
        # 這裡請保留你原本處理時間邏輯的程式碼
        self.result = {"content": "測試", "priority": "中", "category": "一般", "time": "", "time2": ""}
        self.destroy()

    def get_input(self):
        self.master.wait_window(self)
        return self.result

# --- 4. 主程式介面 ---
class TodoApp(ctk.CTk):
    def __init__(self, uid):
        super().__init__()
        global current_uid
        current_uid = uid
        self.title("任務管理系統 - 電腦雲端版")
        center_window(self, 860, 800)
        ctk.set_appearance_mode("light")
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        
        threading.Thread(target=alarm_monitor, daemon=True).start()

        # Header
        self.header = ctk.CTkFrame(self, fg_color="#2D3748", height=85, corner_radius=0)
        self.header.pack(fill="x")
        ctk.CTkLabel(self.header, text="任務管理中心 (雲端同步中)", font=("Microsoft JhengHei", 24, "bold"), text_color="white").place(relx=0.05, rely=0.5, anchor="w")
        self.tray_btn = ctk.CTkButton(self.header, text="📥 縮小", width=70, fg_color="#4A5568", command=self.minimize_to_tray)
        self.tray_btn.place(relx=0.95, rely=0.5, anchor="e")

        # 輸入區
        self.input_card = ctk.CTkFrame(self, fg_color="white", border_width=1, border_color="#E2E8F0")
        self.input_card.pack(pady=20, padx=20, fill="x")
        
        self.entry = ctk.CTkEntry(self.input_card, placeholder_text="新增任務...", width=130, height=45, font=("Microsoft JhengHei", 16), border_width=0, fg_color="transparent")
        self.entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.entry.bind("<Return>", lambda e: self.add_task())

        self.cat_option = ctk.CTkOptionMenu(self.input_card, values=["一般", "工作", "生活", "學習", "健康"], width=75, height=40)
        self.cat_option.pack(side="left", padx=2)
        
        self.priority_option = ctk.CTkOptionMenu(self.input_card, values=["高", "中", "低"], width=65, height=40)
        self.priority_option.pack(side="left", padx=2)

        ctk.CTkButton(self.input_card, text="新增", width=70, height=40, fg_color="#4A5568", font=("Microsoft JhengHei", 15, "bold"), command=self.add_task).pack(side="right", padx=10)

        # 任務列表
        self.task_list_frame = ctk.CTkScrollableFrame(self, fg_color="#F7FAFC", label_text="任務分類視圖", label_font=("Microsoft JhengHei", 18, "bold"))
        self.task_list_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # 啟動時向雲端抓資料
        self.fetch_tasks()

    def fetch_tasks(self):
        """從雲端下載任務"""
        def _fetch():
            try:
                response = requests.get(f"{GAS_API_URL}?uid={current_uid}")
                result = response.json()
                if result.get('status') == 'success':
                    global global_tasks
                    global_tasks = result.get('data', [])
                    # 回到主執行緒更新 UI
                    self.after(0, self.render_tasks)
            except Exception as e:
                print(f"下載資料失敗: {e}")
                self.after(0, lambda: messagebox.showerror("錯誤", "無法連線至雲端伺服器！"))
        
        threading.Thread(target=_fetch, daemon=True).start()

    def render_tasks(self):
        for widget in self.task_list_frame.winfo_children(): 
            widget.destroy()
            
        cat_colors = {"一般": "#F1F5F9", "工作": "#E0F2FE", "生活": "#FEF3C7", "學習": "#F3E8FF", "健康": "#DCFCE7"}
        p_colors = {"高": "#FEE2E2", "中": "#FFEDD5", "低": "#F0FDF4"}
        
        # 排序
        sorted_tasks = sorted(global_tasks, key=lambda x: ({"高":1, "中":2, "低":3}.get(x['priority'], 2), -int(x['id'])))
        
        for task in sorted_tasks:
            item = ctk.CTkFrame(self.task_list_frame, fg_color="white", corner_radius=12, border_width=1, border_color="#E2E8F0")
            item.pack(fill="x", pady=6, padx=10, ipady=5)
            
            content_frame = ctk.CTkFrame(item, fg_color="transparent")
            content_frame.pack(side="left", fill="both", expand=True, padx=15, pady=5)
            
            font_style = ("Microsoft JhengHei", 18, "overstrike") if task['is_completed'] else ("Microsoft JhengHei", 18, "bold")
            text_color = "#94A3B8" if task['is_completed'] else "#1E293B"
            
            lbl = ctk.CTkLabel(content_frame, text=task['content'], font=font_style, text_color=text_color, anchor="w", justify="left")
            lbl.pack(fill="x", anchor="w")
            lbl.bind("<Button-1>", lambda e, i=task['id']: self.toggle_complete(i))
            
            tag_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            tag_frame.pack(fill="x", anchor="w", pady=(6, 0))
            
            c_bg = cat_colors.get(task['category'], "#F1F5F9")
            ctk.CTkLabel(tag_frame, text=task['category'], fg_color=c_bg, width=50, height=22, corner_radius=11, text_color="#333").pack(side="left", padx=(0, 8))
            
            p_bg = p_colors.get(task['priority'], "#F1F5F9")
            ctk.CTkLabel(tag_frame, text=task['priority'], fg_color=p_bg, width=55, height=22, corner_radius=11, text_color="#333").pack(side="left", padx=(0, 8))
            
            if task.get('time'):
                ctk.CTkLabel(tag_frame, text=f"⏰ {task['time']}", text_color="#64748B").pack(side="left")
            
            action_frame = ctk.CTkFrame(item, fg_color="transparent")
            action_frame.pack(side="right", padx=10)
            
            # 省略編輯按鈕，保留刪除功能做示範
            ctk.CTkButton(action_frame, text="🗑️", width=36, height=36, corner_radius=8, fg_color="#F8FAFC", text_color="#E53E3E", hover_color="#FEE2E2", font=("Segoe UI Emoji", 15), 
                          command=lambda i=task['id']: self.delete_task(i)).pack(side="left", padx=4)

    def add_task(self):
        content = self.entry.get().strip()
        if content:
            # 建立新任務物件
            new_task = {
                "id": str(int(time.time() * 1000)),
                "content": content,
                "priority": self.priority_option.get(),
                "category": self.cat_option.get(),
                "time": "", # 若要加入時間，可把之前的 DateEntry 放回來
                "time2": "",
                "is_completed": False
            }
            # 樂觀更新：先寫入本機畫面
            global_tasks.append(new_task)
            self.render_tasks()
            self.entry.delete(0, 'end')
            
            # 背景同步至雲端
            sync_to_cloud("ADD", {"task": new_task})

    def toggle_complete(self, tid):
        for task in global_tasks:
            if task['id'] == tid:
                task['is_completed'] = not task['is_completed']
                self.render_tasks()
                sync_to_cloud("UPDATE", {"task": {"id": tid, "is_completed": task['is_completed']}})
                break

    def delete_task(self, tid):
        if messagebox.askyesno("確認", "確定要刪除嗎？"):
            global global_tasks
            global_tasks = [t for t in global_tasks if t['id'] != tid]
            self.render_tasks()
            sync_to_cloud("DELETE", {"taskId": tid})

    # ... (縮小到工具列的邏輯與原本相同) ...
    def minimize_to_tray(self):
        self.withdraw()
        # ... 省略 ...
        sys.exit()

# --- 5. 登入視窗 (改為輸入 Firebase UID) ---
class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("系統登入")
        center_window(self, 450, 350) 
        self.configure(fg_color="#F0F2F5")
        
        ctk.CTkFrame(self, fg_color="#2D3748", height=15, corner_radius=0).pack(fill="x")
        ctk.CTkLabel(self, text="電腦版雲端登入", font=("Microsoft JhengHei", 28, "bold"), text_color="#333333").pack(pady=40)
        
        # 這裡不再需要密碼，只要驗證身分證 (UID) 就能抓到自己的資料
        self.uid_entry = ctk.CTkEntry(self, placeholder_text="請貼上您的雲端同步碼 (UID)", width=320, height=50, fg_color="white")
        self.uid_entry.pack(pady=10)
        self.uid_entry.bind("<Return>", lambda e: self.login())
        
        ctk.CTkButton(self, text="連線登入", width=320, height=55, corner_radius=10, font=("Microsoft JhengHei", 18, "bold"), fg_color="#4A5568", command=self.login).pack(pady=30)
    
    def login(self):
        uid = self.uid_entry.get().strip()
        if uid: 
            self.destroy()
            TodoApp(uid).mainloop()
        else: 
            messagebox.showerror("失敗", "請輸入同步碼！")

if __name__ == "__main__":
    check_single_instance()
    LoginWindow().mainloop()