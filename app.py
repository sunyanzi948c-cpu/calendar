import customtkinter as ctk
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
import winsound
import socket
import sys
import os
import json
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from tkcalendar import DateEntry
import requests

# ==========================================
# 🚨 請填入你的 Google Apps Script (GAS) API 網址
# ==========================================
GAS_API_URL = "https://script.google.com/macros/s/AKfycbwvYsXf_AQ55AanxcjCfYTzsASRgnqMqZltBxqDY_H8zKZ-aeuRDYaNRnxw0r21sXZd/exec"

CONFIG_FILE = "config.json" # 用來記憶 UID 的檔案

# 全域變數
global_tasks = []
current_uid = ""

# --- 🚀 自動記憶 UID 邏輯 ---
def load_saved_uid():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("uid", "")
        except:
            pass
    return ""

def save_uid(uid):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"uid": uid}, f, ensure_ascii=False)
    except Exception as e:
        print(f"儲存設定檔失敗: {e}")

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

# --- 1. 雲端同步功能 ---
def sync_to_cloud(action, payload):
    def _sync():
        try:
            data = {"uid": current_uid, "action": action}
            data.update(payload)
            requests.post(GAS_API_URL, json=data)
        except Exception as e:
            print(f"雲端同步失敗: {e}")
    threading.Thread(target=_sync, daemon=True).start()

# --- 2. 鬧鐘監控執行緒 ---
def alarm_monitor():
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for task in global_tasks:
                # 容錯處理：將網頁版可能傳來的 "T" 換成空白，確保比對正確
                t_val = task.get('time', '').replace('T', ' ')
                t2_val = task.get('time2', '').replace('T', ' ')
                
                match_time = (t_val == now or t2_val == now)
                
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
                
                elif t_val != now and t2_val != now:
                    task['alarm_triggered'] = False
                    
        except Exception as e:
            print(f"鬧鐘監控發生錯誤: {e}")
            time.sleep(5)
            
        time.sleep(10)

        

# --- 3. 完整編輯彈窗 ---
class EditDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_content, current_priority, current_category, current_time, current_time2=""):
        super().__init__(parent)
        self.title("編輯任務詳情")
        center_window(self, 460, 580)
        self.attributes("-topmost", True)
        self.grab_set()
        self.configure(fg_color="#F0F2F5")
        
        self.result = {"content": None, "priority": None, "category": None, "time": None, "time2": None}
        
        # 標準化時間格式 (處理網頁版傳來的 T)
        current_time = current_time.replace('T', ' ') if current_time else ""
        current_time2 = current_time2.replace('T', ' ') if current_time2 else ""
        
        ctk.CTkLabel(self, text="📝 編輯任務詳情", font=("Microsoft JhengHei", 22, "bold"), text_color="#2D3748").pack(pady=(25, 15))
        
        ctk.CTkLabel(self, text="任務內容", font=("Microsoft JhengHei", 16), text_color="#4A5568").pack(padx=40, anchor="w")
        self.entry = ctk.CTkEntry(self, width=380, height=45, font=("Microsoft JhengHei", 16), fg_color="white", border_color="#D1D5DB")
        self.entry.insert(0, current_content)
        self.entry.pack(pady=5)
        self.entry.focus_set()
        
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(pady=10, padx=40, fill="x")
        
        c_frame = ctk.CTkFrame(row2, fg_color="transparent")
        c_frame.pack(side="left", expand=True)
        ctk.CTkLabel(c_frame, text="分類", font=("Microsoft JhengHei", 16), text_color="#4A5568").pack(anchor="w")
        self.cat_menu = ctk.CTkOptionMenu(c_frame, values=["一般", "工作", "生活", "學習", "健康"], width=110)
        self.cat_menu.set(current_category)
        self.cat_menu.pack(pady=5)
        
        p_frame = ctk.CTkFrame(row2, fg_color="transparent")
        p_frame.pack(side="right", expand=True)
        ctk.CTkLabel(p_frame, text="重要性", font=("Microsoft JhengHei", 16), text_color="#4A5568").pack(anchor="w")
        self.p_menu = ctk.CTkOptionMenu(p_frame, values=["高", "中", "低"], width=110)
        self.p_menu.set(current_priority)
        self.p_menu.pack(pady=5)

        # 鬧鐘主開關
        self.reminder_var = ctk.IntVar(value=1 if current_time else 0)
        self.reminder_cb = ctk.CTkCheckBox(self, text="⏰ 啟用鬧鐘提醒", variable=self.reminder_var, command=self.toggle_reminder, font=("Microsoft JhengHei", 16, "bold"), text_color="#4A5568")
        self.reminder_cb.pack(pady=(15, 0), padx=40, anchor="w")

        time_select_frame = ctk.CTkFrame(self, fg_color="transparent")
        time_select_frame.pack(pady=5)
        
        if current_time and " " in current_time:
            old_d, old_t = current_time.split(" ")
            old_h, old_m = old_t.split(":")
        elif current_time: 
            old_d = datetime.now().strftime("%Y-%m-%d")
            old_h, old_m = current_time.split(":")
        else:
            old_d = datetime.now().strftime("%Y-%m-%d")
            old_h, old_m = datetime.now().strftime("%H"), datetime.now().strftime("%M")
            
        self.d_entry = DateEntry(time_select_frame, width=11, font=("Microsoft JhengHei", 12), background='#4A5568', foreground='white', borderwidth=2, date_pattern='y-mm-dd', mindate=datetime.now().date(), locale='zh_TW') 
        try: self.d_entry.set_date(datetime.strptime(old_d, "%Y-%m-%d").date())
        except ValueError: pass
        self.d_entry.pack(side="left", padx=2, pady=5)
        
        self.today_btn = ctk.CTkButton(time_select_frame, text="今天", width=38, height=26, corner_radius=6, fg_color="#E2E8F0", text_color="#4A5568", hover_color="#CBD5E0", font=("Microsoft JhengHei", 12, "bold"), command=lambda: self.d_entry.set_date(datetime.now().date()))
        self.today_btn.pack(side="left", padx=2)

        self.h_menu = ctk.CTkOptionMenu(time_select_frame, values=[str(i).zfill(2) for i in range(24)], width=70)
        self.h_menu.set(old_h)
        self.h_menu.pack(side="left", padx=2)
        
        self.m_menu = ctk.CTkOptionMenu(time_select_frame, values=[str(i).zfill(2) for i in range(60)], width=70)
        self.m_menu.set(old_m)
        self.m_menu.pack(side="left", padx=2)
        
        # 再次提醒設定
        second_rem_frame = ctk.CTkFrame(self, fg_color="transparent")
        second_rem_frame.pack(pady=(0, 10), padx=40, anchor="w")
        
        old_diff = "10"
        if current_time and current_time2:
            try:
                dt1 = datetime.strptime(current_time, "%Y-%m-%d %H:%M")
                dt2 = datetime.strptime(current_time2, "%Y-%m-%d %H:%M")
                diff = int((dt2 - dt1).total_seconds() / 60)
                if diff > 0: old_diff = str(diff)
            except: pass
            
        self.second_rem_var = ctk.IntVar(value=1 if current_time2 else 0)
        self.second_cb = ctk.CTkCheckBox(second_rem_frame, text="🔁 啟用再次提醒，於", variable=self.second_rem_var, command=self.toggle_second_reminder, font=("Microsoft JhengHei", 14), text_color="#4A5568")
        self.second_cb.pack(side="left", padx=(0, 5))
        
        self.second_menu = ctk.CTkOptionMenu(second_rem_frame, values=["5", "10", "15", "30", "60"], width=65, height=28)
        self.second_menu.set(old_diff)
        self.second_menu.pack(side="left", padx=5)
        
        ctk.CTkLabel(second_rem_frame, text="分鐘後", font=("Microsoft JhengHei", 14), text_color="#4A5568").pack(side="left")
        
        self.toggle_reminder()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=30)
        ctk.CTkButton(btn_frame, text="儲存變更", width=130, height=40, fg_color="#4A5568", text_color="white", command=self.on_confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", width=130, height=40, fg_color="#E2E8F0", text_color="#333333", command=self.destroy).pack(side="left", padx=10)

    def toggle_reminder(self):
        state = "normal" if self.reminder_var.get() == 1 else "disabled"
        self.d_entry.configure(state=state)
        self.today_btn.configure(state=state) 
        self.h_menu.configure(state=state)
        self.m_menu.configure(state=state)
        self.second_cb.configure(state=state)
        if state == "disabled":
            self.second_menu.configure(state="disabled")
            self.second_rem_var.set(0)
        else:
            self.toggle_second_reminder()

    def toggle_second_reminder(self):
        if self.second_rem_var.get() == 1 and self.reminder_var.get() == 1:
            self.second_menu.configure(state="normal")
        else:
            self.second_menu.configure(state="disabled")

    def on_confirm(self):
        rem_time, rem_time2 = "", ""
        if self.reminder_var.get() == 1:
            rem_time = f"{self.d_entry.get()} {self.h_menu.get()}:{self.m_menu.get()}"
            if self.second_rem_var.get() == 1:
                try:
                    dt = datetime.strptime(rem_time, "%Y-%m-%d %H:%M")
                    dt2 = dt + timedelta(minutes=int(self.second_menu.get()))
                    rem_time2 = dt2.strftime("%Y-%m-%d %H:%M")
                except: pass
            
        self.result = {"content": self.entry.get(), "priority": self.p_menu.get(), "category": self.cat_menu.get(), "time": rem_time, "time2": rem_time2}
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
        center_window(self, 900, 800)
        ctk.set_appearance_mode("light")
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        
        threading.Thread(target=alarm_monitor, daemon=True).start()

        # Header
        self.header = ctk.CTkFrame(self, fg_color="#2D3748", height=85, corner_radius=0)
        self.header.pack(fill="x")
        ctk.CTkLabel(self.header, text="任務管理中心 (雲端同步中)", font=("Microsoft JhengHei", 24, "bold"), text_color="white").place(relx=0.05, rely=0.5, anchor="w")

        # 👇 建立一個透明容器，讓裡面的按鈕自動橫向排列 👇
        btn_group = ctk.CTkFrame(self.header, fg_color="transparent")
        btn_group.place(relx=0.97, rely=0.5, anchor="e")

        ctk.CTkButton(btn_group, text="🔄 同步", width=70, fg_color="#4A5568", command=self.fetch_tasks).pack(side="left", padx=5)
        ctk.CTkButton(btn_group, text="⚙️ 切換帳號", width=110, fg_color="#4A5568", command=self.change_uid).pack(side="left", padx=5)
        ctk.CTkButton(btn_group, text="📥 縮小", width=70, fg_color="#4A5568", command=self.minimize_to_tray).pack(side="left", padx=5)

        # 輸入區 (完整加入日期與時間選擇器)
        self.input_card = ctk.CTkFrame(self, fg_color="white", border_width=1, border_color="#E2E8F0")
        self.input_card.pack(pady=20, padx=20, fill="x")
        
        self.entry = ctk.CTkEntry(self.input_card, placeholder_text="新增任務...", width=130, height=45, font=("Microsoft JhengHei", 16), border_width=0, fg_color="transparent")
        self.entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.entry.bind("<Return>", lambda e: self.add_task())

        self.cat_option = ctk.CTkOptionMenu(self.input_card, values=["一般", "工作", "生活", "學習", "健康"], width=75, height=40)
        self.cat_option.set("一般")
        self.cat_option.pack(side="left", padx=2)

        self.date_entry = DateEntry(self.input_card, width=11, font=("Microsoft JhengHei", 12), background='#4A5568', foreground='white', borderwidth=2, date_pattern='y-mm-dd', mindate=datetime.now().date(), locale='zh_TW')
        self.date_entry.pack(side="left", padx=2, ipady=4)

        ctk.CTkButton(self.input_card, text="今天", width=40, height=36, corner_radius=6, fg_color="#E2E8F0", text_color="#4A5568", hover_color="#CBD5E0", font=("Microsoft JhengHei", 13, "bold"), command=lambda: self.date_entry.set_date(datetime.now().date())).pack(side="left", padx=2)

        self.h_menu = ctk.CTkOptionMenu(self.input_card, values=[str(i).zfill(2) for i in range(24)], width=65, height=40)
        self.h_menu.set("時")
        self.h_menu.pack(side="left", padx=2)
        
        self.m_menu = ctk.CTkOptionMenu(self.input_card, values=[str(i).zfill(2) for i in range(60)], width=65, height=40)
        self.m_menu.set("分")
        self.m_menu.pack(side="left", padx=2)

        self.priority_option = ctk.CTkOptionMenu(self.input_card, values=["高", "中", "低"], width=65, height=40)
        self.priority_option.set("中")
        self.priority_option.pack(side="left", padx=2)

        ctk.CTkButton(self.input_card, text="新增", width=70, height=40, fg_color="#4A5568", font=("Microsoft JhengHei", 15, "bold"), command=self.add_task).pack(side="right", padx=10)

        # 任務列表
        self.task_list_frame = ctk.CTkScrollableFrame(self, fg_color="#F7FAFC", label_text="任務分類視圖", label_font=("Microsoft JhengHei", 18, "bold"))
        self.task_list_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.fetch_tasks()

    def change_uid(self):
        if messagebox.askyesno("切換帳號", "是否要登出並清除目前的同步碼？"):
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            self.destroy()
            LoginWindow().mainloop()

    def fetch_tasks(self):
        def _fetch():
            try:
                response = requests.get(f"{GAS_API_URL}?uid={current_uid}")
                result = response.json()
                if result.get('status') == 'success':
                    global global_tasks
                    global_tasks = result.get('data', [])
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
            
            time_tag = ""
            if task.get('time'):
                t_val = task['time'].replace('T', ' ')[:16] # 截斷秒數與 T
                time_tag += f"⏰ {t_val}"
                t2_val = task.get('second_reminder_time') or task.get('time2')
                if t2_val:
                    t2_only = t2_val.replace('T', ' ')
                    t2_only = t2_only.split(' ')[1] if ' ' in t2_only else t2_only
                    time_tag += f"  🔁 {t2_only[:5]}"
                ctk.CTkLabel(tag_frame, text=time_tag, text_color="#64748B").pack(side="left")
            
            action_frame = ctk.CTkFrame(item, fg_color="transparent")
            action_frame.pack(side="right", padx=10)
            
            # 加入編輯按鈕
            t = task.get('time', '').replace('T', ' ')[:16]
            t2 = task.get('time2', '').replace('T', ' ')[:16]
            ctk.CTkButton(action_frame, text="✏️", width=36, height=36, corner_radius=8, fg_color="#F8FAFC", text_color="#3182CE", hover_color="#E2E8F0", font=("Segoe UI Emoji", 15), 
                          command=lambda i=task['id'], c=task['content'], p=task['priority'], cat=task['category'], t=t, t2=t2: self.edit_task(i, c, p, cat, t, t2)).pack(side="left", padx=4)
            
            ctk.CTkButton(action_frame, text="🗑️", width=36, height=36, corner_radius=8, fg_color="#F8FAFC", text_color="#E53E3E", hover_color="#FEE2E2", font=("Segoe UI Emoji", 15), 
                          command=lambda i=task['id']: self.delete_task(i)).pack(side="left", padx=4)

    def add_task(self):
        content = self.entry.get().strip()
        if content:
            d = self.date_entry.get()
            h = self.h_menu.get()
            m = self.m_menu.get()
            rem_time = f"{d} {h}:{m}" if h != "時" and m != "分" else ""
            
            new_task = {
                "id": str(int(time.time() * 1000)),
                "content": content,
                "priority": self.priority_option.get(),
                "category": self.cat_option.get(),
                "time": rem_time,
                "time2": "",
                "is_completed": False
            }
            global_tasks.append(new_task)
            self.render_tasks()
            self.entry.delete(0, 'end')
            sync_to_cloud("ADD", {"task": new_task})

    def edit_task(self, tid, c, p, cat, t, t2):
        res = EditDialog(self, c, p, cat, t, t2).get_input()
        if res["content"] is not None:
            for task in global_tasks:
                if task['id'] == tid:
                    task['content'] = res["content"].strip()
                    task['priority'] = res["priority"]
                    task['category'] = res["category"]
                    task['time'] = res["time"]
                    task['time2'] = res["time2"]
                    self.render_tasks()
                    sync_to_cloud("UPDATE", {"task": task})
                    break

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

    def create_image(self):
        image = Image.new('RGB', (64, 64), color=(45, 55, 72))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
        return image

    def minimize_to_tray(self):
        self.withdraw()
        image = self.create_image()
        menu = (item('顯示', self.show_window), item('退出', self.quit_window))
        self.tray_icon = pystray.Icon("todo_tray", image, "任務管理系統", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self): 
        self.tray_icon.stop()
        self.after(0, self.deiconify)
        
    def quit_window(self): 
        self.tray_icon.stop()
        self.destroy()
        sys.exit()

# --- 5. 登入視窗 ---
class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("系統登入")
        center_window(self, 450, 350) 
        self.configure(fg_color="#F0F2F5")
        
        ctk.CTkFrame(self, fg_color="#2D3748", height=15, corner_radius=0).pack(fill="x")
        ctk.CTkLabel(self, text="電腦版雲端登入", font=("Microsoft JhengHei", 28, "bold"), text_color="#333333").pack(pady=40)
        
        self.uid_entry = ctk.CTkEntry(self, placeholder_text="請貼上您的雲端同步碼 (UID)", width=320, height=50, fg_color="white")
        self.uid_entry.pack(pady=10)
        self.uid_entry.bind("<Return>", lambda e: self.login())
        
        ctk.CTkButton(self, text="連線登入", width=320, height=55, corner_radius=10, font=("Microsoft JhengHei", 18, "bold"), fg_color="#4A5568", command=self.login).pack(pady=30)
    
    def login(self):
        uid = self.uid_entry.get().strip()
        if uid: 
            save_uid(uid)
            self.destroy()
            TodoApp(uid).mainloop()
        else: 
            messagebox.showerror("失敗", "請輸入同步碼！")

if __name__ == "__main__":
    check_single_instance()
    
    saved_uid = load_saved_uid()
    if saved_uid:
        TodoApp(saved_uid).mainloop()
    else:
        LoginWindow().mainloop()