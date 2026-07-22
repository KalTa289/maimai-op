import tkinter as tk
from tkinter import ttk
import json

def load_data():
    try:
        with open("data/versions_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

root = tk.Tk()
root.title("maimai-op")
root.geometry("600x400")

columns = ("version", "version_op", "version_max_op", "op_percent")
tree = ttk.Treeview(root, columns=columns, show="headings")

tree.heading("version", text="Version")
tree.heading("version_op", text="OP")
tree.heading("version_max_op", text="Max OP")
tree.heading("op_percent", text="OP %")

tree.column("version", width=150, anchor="center")
tree.column("version_op", width=100, anchor="center")
tree.column("version_max_op", width=100, anchor="center")
tree.column("op_percent", width=100, anchor="center")

scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
tree.pack(side="left", fill="both", expand=True)

# define row colors
tree.tag_configure("plate_1", background="#74cdff") # silver
tree.tag_configure("plate_2", background="#fffe1b") # gold
tree.tag_configure("plate_3", background="#fff3c1") # platinum
tree.tag_configure("plate_4", background="#f1d3fb") # rainbow

data = load_data()
total_charts = 0

for item in data:
    pos = item.get("possession", 0)
    v_op = item.get("version_op", 0.0)
    v_max = item.get("version_max_op", 0.0)
    op_val = item.get("op_percent", 0.0)
    
    row_tag = f"plate_{pos}" if pos > 0 else ""
    op_str = f"{op_val}%"
    
    tree.insert(
        "",
        "end",
        values=(
            item.get("version", ""),
            round(v_op, 2),
            round(v_max, 2),
            op_str
        ),
        tags=(row_tag,) if row_tag else ()
    )
root.mainloop()