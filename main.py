import tkinter as tk
import requests
import json
import webbrowser
import time
from pathlib import Path

Client_ID = "Ov23lidpJYZy5bxKdEbP"

BG_Color = "#0d1117"
Text_1 = '#e6edf3'
Text_2 = '#8b949e'
Text_Muted = "#484f58"
Blue = "#58a6ff"
Green = "#3fb950"
Danger = "#f85149"

root = tk.Tk()

root = tk.Tk()
root.title("GitHub Widget")
root.geometry("380x580")
root.attributes('-topmost', True)
root.overrideredirect(True)
root.attributes('-alpha', 0.9)
root.configure(bg = BG_Color)

drag_data = {"x": 0, "y": 0}
def start_drag(e):
    drag_data["x"] = e.x_root - root.winfo_x ()
    drag_data["y"] =e.y_root - root.winfo_y ()
    
root.bind("<Button-1>", start_drag)
root.bind("<B1-Motion>", lambda e: root.geometry(f"+{e.x_root - drag_data['x']}+{e.y_root - drag_data['y']}"))

close = tk.Label(root, text="X", font=("Sans-serif",14), fg="white", bg = BG_Color, cursor="hand2")
close.pack(anchor="ne", padx=10, pady=5)
close.bind("<Button-1>", lambda e: root.destroy())

main = tk.Frame(root, bg = BG_Color)
main.pack(fill="both", expand=True, padx=16, pady=16) 

main = tk.Frame(root, bg = BG_Color)
main.pack(fill = "both", expand = True, padx = 16, pady =16)

login = None

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
            except Exception as e:
                self.token = None
                self.username = None
                try: 
                    self.token_file.unlink()
                except:
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
        except:
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
            except:
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
                    headers = {"Accept": "application/json"},
                    data = poll_data
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
        

root.mainloop()