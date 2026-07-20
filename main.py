import tkinter as tk

root = tk.Tk()
root.title("GitHub Widget")
root.geometry("380x580")
root.attributes('-topmost', True)
root.overrideredirect(True)
root.attributes('-alpha', 0.9)
root.configure(bg='#0d1117')

drag_data = {"x": 0, "y": 0}
def start_drag(e):
    drag_data["x"] = e.x_root - root.winfo_x ()
    drag_data["y"] =e.y_root - root.winfo_y ()
    
root.bind("<Button-1>", start_drag)
root.bind("<B1-Motion>", do_drag)

close = tk.Label(root, text="X", font=("Sans-serif",14), fg="white", bg='#0d1117', cursor="hand2")

root.mainloop()