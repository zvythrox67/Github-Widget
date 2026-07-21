import tkinter as tk
import requests
import json
import webbrowser
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import platform

Client_ID = "Ov23lidpJYZy5bxKdEbP"

BG_Color = "#0d1117"
BG_CARD = "#161b22"
BG_HOVER = "#21262d"
Text_1 = '#e6edf3'
Text_2 = '#8b949e'
Text_Muted = "#484f58"
Blue = "#58a6ff"
Green = "#3fb950"
Red = "#f85149"

CAL_COLORS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
    5: "#1f2937"
}

root = tk.Tk()
root.title("GitHub Widget")
root.geometry("350x600")
root.attributes('-topmost', True)
root.overrideredirect(True)
root.attributes('-alpha', 0.9)
root.configure(bg=BG_Color)
root.resizable(False, False)

drag_data = {"x": 0, "y": 0}
def start_drag(e):
    drag_data["x"] = e.x_root - root.winfo_x()
    drag_data["y"] = e.y_root - root.winfo_y()

root.bind("<Button-1>", start_drag)
root.bind("<B1-Motion>", lambda e: root.geometry(f"+{e.x_root - drag_data['x']}+{e.y_root - drag_data['y']}"))

close_btn = tk.Label(root, text="\u2715", font=("Segoe UI", 12), fg=Text_2, bg=BG_Color, cursor="hand2")
close_btn.place(relx=1.0, x=-14, y=8, anchor="ne")
close_btn.bind("<Button-1>", lambda e: root.destroy())
close_btn.bind("<Enter>", lambda e: close_btn.config(fg=Text_1))
close_btn.bind("<Leave>", lambda e: close_btn.config(fg=Text_2))

main = tk.Frame(root, bg=BG_Color)
main.pack(fill="both", expand=True, padx=16, pady=16)

login = None
floating_icon = None
main_view = None


class GitHubOAuth:
    def __init__(self):
        self.token = None
        self.username = None
        self.token_file = Path.home() / ".github_widget_token"
        self.checked = False
        self.load_token()

    def load_token(self):
        if self.token_file.exists():
            try:
                data = json.loads(self.token_file.read_text())
                temp_token = data.get('token')
                temp_username = data.get('username')

                if temp_token and temp_username:
                    self.token = temp_token
                    self.username = temp_username
                    return True
                else:
                    self.token = None
                    self.username = None
                    self.token_file.unlink()
            except Exception:
                self.token = None
                self.username = None
                try:
                    self.token_file.unlink()
                except Exception:
                    pass
        self.token = None
        self.username = None
        return False

    def _test_token_sync(self):
        if not self.token:
            return False
        try:
            headers = {"Authorization": f"token {self.token}"}
            resp = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def test_token(self):
        if not self.token:
            return False
        return self._test_token_sync()

    def save_token(self):
        if self.token and self.username:
            data = {'token': self.token, 'username': self.username}
            self.token_file.write_text(json.dumps(data))
            self.token_file.chmod(0o600)

    def logout(self):
        self.token = None
        self.username = None
        if self.token_file.exists():
            try:
                self.token_file.unlink()
            except Exception:
                pass

    def device_flow_login(self, callback):
        try:
            data = {"client_id": Client_ID, "scope": "read:user"}
            resp = requests.post(
                "https://github.com/login/device/code",
                headers={"Accept": "application/json"},
                data=data
            )

            if resp.status_code != 200:
                callback("error", "Failed to start login.")
                return False

            device_data = resp.json()
            device_code = device_data['device_code']
            user_code = device_data['user_code']
            verification_uri = device_data['verification_uri']
            interval = device_data.get('interval', 5)

            callback("code", f"open: {verification_uri}\nCode: {user_code}")
            webbrowser.open(verification_uri)

            poll_data = {
                "client_id": Client_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
            }

            while True:
                time.sleep(interval)
                resp = requests.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data=poll_data
                )

                if resp.status_code == 200:
                    token_data = resp.json()
                    if 'access_token' in token_data:
                        self.token = token_data['access_token']
                        headers = {"Authorization": f"token {self.token}"}
                        user_resp = requests.get("https://api.github.com/user", headers=headers)

                        if user_resp.status_code == 200:
                            self.username = user_resp.json().get('login')
                            self.save_token()
                            callback("success", f"Connected as {self.username}")
                            return True
                    elif 'error' in token_data:
                        error = token_data['error']
                        if error == 'authorization_pending':
                            continue
                        elif error == 'slow_down':
                            interval += 2
                            continue
                        else:
                            callback("error", f"Login error: {error}")
                            return False
                else:
                    callback("error", "Failed to get access token")
                    return False
        except Exception as e:
            callback("error", f"Login error: {str(e)[:100]}")
            return False


class GitHubAPI:
    def __init__(self, oauth):
        self.oauth = oauth

    def get_headers(self):
        return {"Authorization": f"token {self.oauth.token}"}

    def get_all_events(self):
        if not self.oauth.token or not self.oauth.username:
            return None

        all_events = []
        page = 1

        while True:
            url = f"https://api.github.com/users/{self.oauth.username}/events"
            params = {"per_page": 100, "page": page}

            try:
                resp = requests.get(
                    url,
                    headers=self.get_headers(),
                    params=params,
                    timeout=10
                )

                if resp.status_code == 401:
                    print("Token Expired. Please login again.")
                    return None

                if resp.status_code != 200:
                    break

                events = resp.json()
                if not events:
                    break

                all_events.extend(events)

                oldest = events[-1].get('created_at', '')
                if oldest:
                    oldest_date = datetime.fromisoformat(oldest.replace('Z', '+00:00'))
                    if (datetime.now() - oldest_date).days > 90:
                        break
                page += 1

            except Exception as e:
                print(f"Error loading page {page}: {e}")
                break

        return all_events if all_events else None

    def get_streak_data(self):
        events = self.get_all_events()
        if not events:
            return None, None, None

        commit_dates = []
        for event in events:
            if event.get('type') == 'PushEvent':
                date = event.get('created_at', '').split('T')[0]
                if date:
                    commits = event.get('payload', {}).get('commits', [])
                    commit_count = len(commits) if commits else 1
                    for _ in range(commit_count):
                        commit_dates.append(date)

        if not commit_dates:
            return 0, 0, {}

        daily_counts = Counter(commit_dates)
        total_commits = len(commit_dates)

        today = datetime.now().date()
        streak = 0
        check_date = today

        while True:
            date_str = str(check_date)
            if date_str in daily_counts:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        calender = {}
        for i in range(49):
            date = today - timedelta(days=i)
            calender[str(date)] = daily_counts.get(str(date), 0)

        return streak, total_commits, calender

    def get_last_commit_info(self):
        events = self.get_all_events()
        if not events:
            return None, None

        for event in events:
            if event.get('type') == 'PushEvent':
                repo = event.get('repo', {}).get('name', 'Unknown')
                created_at = event.get('created_at', '')
                if created_at:
                    commit_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    return repo, commit_time

        return None, None


class LoginScreen:
    def __init__(self, parent, on_login_success):
        self.parent = parent
        self.on_login_success = on_login_success
        self.oauth = GitHubOAuth()
        self.frame = tk.Frame(parent, bg=BG_Color)
        self.frame.pack(fill='both', expand=True)
        self.create_ui()

    def create_ui(self):
        login_frame = tk.Frame(self.frame, bg=BG_CARD)
        login_frame.pack(expand=True, fill='both', padx=20, pady=20)

        tk.Label(login_frame, text="\U0001F510", font=('Segoe UI', 20), fg=Blue, bg=BG_CARD).pack(pady=(30, 10))
        tk.Label(login_frame, text="Connect Github", font=('Segoe UI', 10, 'bold'), fg=Text_1, bg=BG_CARD).pack()
        tk.Label(login_frame, text="Sign in to see your streak", font=('Segoe UI', 10), fg=Text_2, bg=BG_CARD).pack(pady=(5, 20))

        login_btn = tk.Label(login_frame, text="Sign in with Github", font=('Segoe UI', 12, 'bold'), fg='white', bg=Blue, cursor='hand2', padx=20, pady=8)
        login_btn.pack(pady=10)
        login_btn.bind('<Button-1>', lambda e: self.start_login())
        login_btn.bind('<Enter>', lambda e: login_btn.config(bg='#1f6feb'))
        login_btn.bind('<Leave>', lambda e: login_btn.config(bg=Blue))

        self.status = tk.Label(login_frame, text="", font=('Segoe UI', 9), fg=Text_2, bg=BG_CARD)
        self.status.pack(pady=10)

        tk.Label(login_frame, text="Your token is stored locally", font=('Segoe UI', 7), fg=Text_Muted, bg=BG_CARD).pack(side='bottom', pady=10)

    def start_login(self):
        self.status.config(text="Starting login...")
        import threading
        threading.Thread(target=self._do_login, daemon=True).start()

    def _do_login(self):
        def callback(status, message):
            self.parent.after(0, lambda: self._login_callback(status, message))
        self.oauth.device_flow_login(callback)

    def _login_callback(self, status, message):
        if status == "code":
            self.status.config(text="Enter this code in browser")
            parts = message.split('\n')
            if len(parts) > 1:
                code = parts[1].replace('Code:', '')
                code_frame = tk.Frame(self.frame, bg=BG_CARD)
                code_frame.pack(pady=5)
                tk.Label(code_frame, text=code, font=('Courier', 20, 'bold'), fg='white', bg='#1f2937', padx=20, pady=10).pack()

        elif status == "success":
            self.status.config(text=f"Success {message}")
            self.status.config(fg=Green)
            self.parent.after(1000, self.on_login_success)

        elif status == "error":
            self.status.config(text=f"error {message}")
            self.status.config(fg=Red)


class FloatingIcon:
    def __init__(self, root, on_click_callback):
        self.root = root
        self.on_click_callback = on_click_callback
        self.is_visible = True

        self.icon_window = tk.Toplevel(root)
        self.icon_window.overrideredirect(True)
        self.icon_window.attributes('-topmost', True)

        transparent_key = "#123456"
        self.icon_window.configure(bg=transparent_key)
        try:
            self.icon_window.attributes('-transparentcolor', transparent_key)
        except tk.TclError:
            try:
                self.icon_window.attributes('-transparent', True)
            except tk.TclError:
                pass 
            
        size = 55
        self.icon_window.geometry(f"{size}x{size}")

        screen_width = self.icon_window.winfo_screenwidth()
        screen_height = self.icon_window.winfo_screenheight()
        self.icon_window.geometry(f"+{screen_width - size - 20}+{screen_height - size - 40}")

        system = platform.system()
        if system == "Windows":
            emoji_font = ("Segoe UI Emoji", 30)
        elif system == "Darwin":
            emoji_font = ("Apple Color Emoji", 30)
        else:
            emoji_font = ("Noto Color Emoji", 30)

        self.canvas = tk.Canvas(
            self.icon_window,
            width=size, height=size,
            bg=transparent_key, bd=0, highlightthickness=0,
            cursor='hand2'
        )
        self.canvas.pack(fill='both', expand=True)

        flame_id = self.canvas.create_text(
            size / 2, size / 2,
            text="\U0001F525", font=emoji_font, fill="#f0883e", tags='flame'
        )
        self.canvas.tag_raise(flame_id) 

        self.canvas.bind('<Button-1>', self.on_click)
        self.drag_data = {"x": 0, "y": 0}
        self.canvas.bind('<Button-3>', self.start_drag)
        self.canvas.bind('<B3-Motion>', self.do_drag)

        self.hide()

    def on_click(self, event):
        self.hide()
        self.on_click_callback()

    def start_drag(self, event):
        self.drag_data["x"] = event.x_root - self.icon_window.winfo_x()
        self.drag_data["y"] = event.y_root - self.icon_window.winfo_y()

    def do_drag(self, event):
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        self.icon_window.geometry(f"+{x}+{y}")

    def show(self):
        self.icon_window.deiconify()
        self.icon_window.lift()
        self.is_visible = True

    def hide(self):
        self.icon_window.withdraw()
        self.is_visible = False

    def toggle(self):
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def destroy(self):
        self.icon_window.destroy()


class MainView:
    def __init__(self, parent, oauth, on_logout, on_minimize):
        self.parent = parent
        self.oauth = oauth
        self.on_logout = on_logout
        self.on_minimize = on_minimize
        self.api = GitHubAPI(oauth)

        self.frame = tk.Frame(parent, bg=BG_Color)
        self.frame.pack(fill='both', expand=True)

        self.create_ui()
        self.refresh_data()
        self.start_auto_refresh()

    def create_ui(self):
        header = tk.Frame(self.frame, bg=BG_Color)
        header.pack(fill='x', pady=(0, 12))

        tk.Label(header, text=f"\U0001F525 {self.oauth.username}", font=('Segoe UI', 9, 'bold'), fg=Text_2, bg=BG_Color).pack(side='left')

        minimize_btn = tk.Label(header, text="\u2796", font=('Segoe UI', 14), fg=Text_2, bg=BG_Color, cursor='hand2')
        minimize_btn.pack(side='right', padx=5)
        minimize_btn.bind('<Button-1>', lambda e: self.minimize_to_icon())

        streak_frame = tk.Frame(self.frame, bg=BG_CARD, relief='flat', bd=1)
        streak_frame.pack(fill='x', pady=(0, 12))

        repo_frame = tk.Frame(self.frame, bg=BG_CARD, relief='flat', bd=1)
        repo_frame.pack(fill='x', pady=(0, 12))

        self.repo_label = tk.Label(repo_frame, text="Loading repo info...", font=('Segoe UI', 9), fg=Text_2, bg=BG_CARD)
        self.repo_label.pack(side='left', padx=16, pady=8)

        self.streak_label = tk.Label(streak_frame, text="--", font=('Segoe UI', 20, 'bold'), fg=Blue, bg=BG_CARD)
        self.streak_label.pack(side='left', padx=20, pady=12)

        info = tk.Frame(streak_frame, bg=BG_CARD)
        info.pack(side='left', padx=(0, 20))

        tk.Label(info, text="DAY STREAK", font=('Segoe UI', 9), fg=Text_2, bg=BG_CARD).pack(anchor='w')

        self.total_label = tk.Label(info, text="Loading...", font=('Segoe UI', 8), fg=Text_2, bg=BG_CARD)
        self.total_label.pack(anchor='w')

        refresh = tk.Label(streak_frame, text="\u27f3", font=('Segoe UI', 10), fg=Text_2, bg=BG_CARD, cursor='hand2')
        refresh.pack(side='right', padx=12)
        refresh.bind('<Button-1>', lambda e: self.refresh_data())

        calendar_container = tk.Frame(self.frame, bg=BG_Color)
        calendar_container.pack(fill='both', expand=True, pady=(0, 8))

        cal_canvas = tk.Canvas(calendar_container, bg=BG_Color, highlightthickness=0)
        cal_scrollbar = tk.Scrollbar(calendar_container, orient="vertical", command=cal_canvas.yview)
        cal_frame = tk.Frame(cal_canvas, bg=BG_Color)

        cal_frame.bind("<Configure>", lambda e: cal_canvas.configure(scrollregion=cal_canvas.bbox("all")))

        cal_canvas.create_window((0, 0), window=cal_frame, anchor="nw")
        cal_canvas.configure(yscrollcommand=cal_scrollbar.set)

        cal_canvas.pack(side="left", fill="both", expand=True)
        cal_scrollbar.pack(side="right", fill="y")

        for i in range(7):
            cal_frame.grid_columnconfigure(i, weight=1)

        days = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
        for i, day in enumerate(days):
            tk.Label(cal_frame, text=day, font=('Segoe UI', 8), fg=Text_Muted, bg=BG_Color).grid(row=0, column=i, padx=1, pady=(0, 3), sticky='nsew')

        self.cells = []
        self.cell_dates = []

        for r in range(15):
            row_cells = []
            row_dates = []
            for c in range(7):
                cell = tk.Label(cal_frame, width=5, height=1, bg=CAL_COLORS[0], relief='flat')
                cell.grid(row=r + 1, column=c, padx=1, pady=2, sticky='nsew')
                row_cells.append(cell)
                row_dates.append(None)
            self.cells.append(row_cells)
            self.cell_dates.append(row_dates)

        self.cal_canvas = cal_canvas
        self.cal_frame = cal_frame

        self.status = tk.Label(self.frame, text="Loading data...", font=('Segoe UI', 8), fg=Text_Muted, bg=BG_Color)
        self.status.pack(pady=(10, 0))

        logout_frame = tk.Frame(self.frame, bg=BG_Color)
        logout_frame.pack(fill='x', pady=(16, 4))

        logout_btn = tk.Label(logout_frame, text="\U0001F6AA Logout", font=('Segoe UI', 10), fg=Text_2, bg=BG_HOVER, cursor='hand2', padx=16, pady=6)
        logout_btn.pack(side='bottom')
        logout_btn.bind('<Button-1>', lambda e: self.do_logout())
        logout_btn.bind('<Enter>', lambda e: logout_btn.config(bg='#30363d'))
        logout_btn.bind('<Leave>', lambda e: logout_btn.config(bg=BG_HOVER))

    def do_logout(self):
        self.oauth.logout()
        self.on_logout()

    def minimize_to_icon(self):
        self.frame.pack_forget()
        root.withdraw()
        if self.on_minimize:
            self.on_minimize()

    def show(self):
        self.frame.pack(fill='both', expand=True)
        root.deiconify()
        root.lift()

    def refresh_data(self):
        self.status.config(text="Fetching Github data...")
        import threading
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _update_ui(self, streak, total, calender, repo=None, last_commit_time=None):
        if streak is None:
            self.streak_label.config(text="\u26a0\ufe0f", fg=Red)
            self.total_label.config(text="Error loading")
            self.status.config(text=" Check network or login again")
            return

        self.streak_label.config(text=str(streak), fg=Blue)
        self.total_label.config(text=f"{total} commits (90 days)")

        if repo:
            time_str = "Today" if last_commit_time.date() == datetime.now().date() else last_commit_time.strftime('%b %d')
            self.repo_label.config(text=f"\U0001F4C1 {repo}  \u2022  Last commit: {time_str}")
        else:
            self.repo_label.config(text="\U0001F4C1 No recent commits found")

        if calender:
            today = datetime.now().date()

            dates = sorted(calender.keys())
            if dates:
                earliest = datetime.strptime(dates[0], '%Y-%m-%d').date()

                days_range = (today - earliest).days + 1
                weeks_needed = (days_range // 7) + 2

                while len(self.cells) < weeks_needed + 1:
                    row_cells = []
                    row_dates = []
                    for c in range(7):
                        cell = tk.Label(self.cal_frame, width=5, height=1, bg=CAL_COLORS[0], relief='flat')
                        cell.grid(row=len(self.cells) + 1, column=c, padx=1, pady=2, sticky='nsew')
                        row_cells.append(cell)
                        row_dates.append(None)
                    self.cells.append(row_cells)
                    self.cell_dates.append(row_dates)

                days_since_monday = earliest.weekday()
                start_date = earliest - timedelta(days=days_since_monday)

                for r in range(len(self.cells)):
                    for c in range(7):
                        date = start_date + timedelta(days=(r * 7 + c))
                        date_str = str(date)

                        self.cell_dates[r][c] = date

                        if date > today:
                            self.cells[r][c].config(bg=CAL_COLORS[5])
                            self.cells[r][c].unbind('<Enter>')
                            self.cells[r][c].unbind('<Leave>')
                        elif date_str in calender:
                            count = calender[date_str]
                            if count == 0:
                                color = CAL_COLORS[0]
                            elif count <= 2:
                                color = CAL_COLORS[1]
                            elif count <= 4:
                                color = CAL_COLORS[2]
                            elif count <= 6:
                                color = CAL_COLORS[3]
                            else:
                                color = CAL_COLORS[4]

                            self.cells[r][c].config(bg=color)

                            self.cells[r][c].bind('<Enter>', lambda e, d=date_str, c=count: self.status.config(text=f"{d}: {c} commit{'s' if c != 1 else ''}"))
                            self.cells[r][c].bind('<Leave>', lambda e: self.status.config(text=f"Updated {datetime.now().strftime('%H:%M')}"))
                        else:
                            self.cells[r][c].config(bg=CAL_COLORS[0])

                self.cal_canvas.configure(scrollregion=self.cal_canvas.bbox("all"))

    def start_auto_refresh(self):
        self.frame.after(300000, self._auto_refresh_loop)

    def _auto_refresh_loop(self):
        self.refresh_data()
        self.frame.after(300000, self._auto_refresh_loop)

    def _fetch_data(self):
        streak, total, calender = self.api.get_streak_data()
        repo, last_commit_time = self.api.get_last_commit_info()
        self.frame.after(0, lambda: self._update_ui(streak, total, calender, repo, last_commit_time))


def show_login():
    global login, floating_icon

    if floating_icon:
        floating_icon.hide()
    root.deiconify()

    for widget in main.winfo_children():
        widget.destroy()
    login = LoginScreen(main, show_main)
    main.login = login


def show_main():
    global login, main_view, floating_icon

    if floating_icon:
        floating_icon.hide()
    root.deiconify()

    for widget in main.winfo_children():
        widget.destroy()
    main_view = MainView(main, login.oauth, show_login, show_floating_icon)
    main.main_view = main_view


def show_main_with_oauth(oauth):
    global main_view

    for widget in main.winfo_children():
        widget.destroy()
    main_view = MainView(main, oauth, show_login, show_floating_icon)
    main.main_view = main_view


def show_floating_icon():
    global floating_icon

    if floating_icon is None:
        floating_icon = FloatingIcon(root, on_icon_click)
    floating_icon.show()


def on_icon_click():
    global floating_icon, main_view

    if floating_icon:
        floating_icon.hide()

    if main_view:
        main_view.show()
    else:
        check_login_status()


def check_login_status():
    global login, floating_icon

    if floating_icon:
        floating_icon.hide()

    oauth = GitHubOAuth()

    if oauth.token and oauth.username:
        def verify():
            if oauth.test_token():
                root.after(0, lambda: show_main_with_oauth(oauth))
            else:
                root.after(0, show_login)

        import threading
        threading.Thread(target=verify, daemon=True).start()
    else:
        show_login()


check_login_status()

root.mainloop()