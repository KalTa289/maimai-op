import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import ImageTk
import threading
import ctypes
from pathlib import Path

from calculate import calculate_for_user, load_json, level_sort_key
from sync import sync_sega_direct
from card_generator import generate_gradient_badge, PLATE_COLORS, PLATE_NAMES, get_op_tier_color

PLATE_NAMES = {4: "Rainbow", 3: "Platinum", 2: "Gold", 1: "Silver", 0: "—"}

DARK_THEME = {
    "bg_main": "#18191c",
    "bg_card": "#22252a",
    "bg_input": "#2a2d34",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "accent": "#38bdf8",
    "grid_line": "#2a2d34",
    "tree_bg": "#1e2024",
    "tree_head_bg": "#282b32",
}

def set_windows_dark_titlebar(root):
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        val = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass

def format_delta(val, is_percent=False):
    if val is None or abs(val) < 0.0001:
        return "—"
    sign = "+" if val > 0 else ""
    suffix = "%" if is_percent else ""
    return f"{sign}{val:.2f}{suffix}"

class HistoryGraphCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=DARK_THEME["bg_card"], bd=0, highlightthickness=0, **kwargs)
        self.points = []
        self.dot_coords = []
        self.bind("<Configure>", lambda e: self.draw_graph())
        self.bind("<Motion>", self.on_mouse_move)
        self.bind("<Leave>", lambda e: self.delete("tooltip"))

    def set_data(self, history_snapshots):
        self.points = []
        for snap in history_snapshots:
            ts = snap.get("timestamp", "")
            plays = snap.get("play_count", "")
            all_item = next((i for i in snap.get("data", []) if i.get("version") == "ALL"), None)
            if all_item:
                op = float(all_item.get("version_op", 0.0))
                max_op = float(all_item.get("version_max_op", 0.0))
                pct = (op / max_op * 100) if max_op > 0 else 0.0
                self.points.append({"timestamp": ts, "play_count": plays, "op": op, "max_op": max_op, "pct": pct})
        self.draw_graph()

    def draw_graph(self):
        self.delete("all")
        self.dot_coords = []
        w, h = self.winfo_width(), self.winfo_height()
        if w < 100 or h < 80:
            return

        if not self.points:
            self.create_text(w // 2, h // 2, text="No historical snapshots recorded yet.", fill=DARK_THEME["text_secondary"], font=("Helvetica", 11))
            return

        pad_l, pad_r, pad_t, pad_b = 65, 35, 35, 45
        plot_w, plot_h = w - pad_l - pad_r, h - pad_t - pad_b

        ops = [p["op"] for p in self.points]
        min_op, max_op = min(ops), max(ops)
        margin = max(10.0, (max_op - min_op) * 0.20) if max_op != min_op else 50
        y_min, y_max = max(0, min_op - margin), max_op + margin

        for i in range(5):
            y_val = y_min + (y_max - y_min) * (i / 4)
            y_pos = pad_t + plot_h - (i / 4) * plot_h
            self.create_line(pad_l, y_pos, w - pad_r, y_pos, fill=DARK_THEME["grid_line"], dash=(3, 3))
            self.create_text(pad_l - 8, y_pos, text=f"{y_val:,.0f}", fill=DARK_THEME["text_secondary"], font=("Helvetica", 8), anchor="e")

        n = len(self.points)
        coords = []
        for i, p in enumerate(self.points):
            x = (pad_l + plot_w / 2) if n == 1 else pad_l + (i / (n - 1)) * plot_w
            y_ratio = (p["op"] - y_min) / (y_max - y_min) if (y_max > y_min) else 0.5
            y = pad_t + plot_h - (y_ratio * plot_h)
            coords.append((x, y))
            self.dot_coords.append((x, y, p, i))

            label = f"#{p['play_count']}" if p.get("play_count") else p["timestamp"][5:16]
            self.create_text(x, h - pad_b + 14, text=label, fill=DARK_THEME["text_secondary"], font=("Helvetica", 8), anchor="center")

        if len(coords) >= 2:
            poly = [coords[0][0], pad_t + plot_h]
            for cx, cy in coords:
                poly.extend([cx, cy])
            poly.extend([coords[-1][0], pad_t + plot_h])
            self.create_polygon(poly, fill="#0f2942", outline="")

            flat = [v for pt in coords for v in pt]
            self.create_line(flat, fill=DARK_THEME["accent"], width=3, smooth=False)

        for x, y, p, _ in self.dot_coords:
            self.create_oval(x - 5, y - 5, x + 5, y + 5, fill=DARK_THEME["accent"], outline="#ffffff", width=2)
            self.create_text(x, y - 12, text=f"{p['op']:,.1f}", fill=DARK_THEME["text_primary"], font=("Helvetica", 8, "bold"))

    def on_mouse_move(self, event):
        mx, my = event.x, event.y
        closest = next(((x, y, p, idx) for x, y, p, idx in self.dot_coords if ((mx - x)**2 + (my - y)**2)**0.5 < 22), None)
        if not closest:
            self.delete("tooltip")
            return

        x, y, p, idx = closest
        self.delete("tooltip")
        d_str = f"{'+' if (p['op'] - self.points[idx-1]['op']) > 0 else ''}{p['op'] - self.points[idx-1]['op']:,.2f}" if idx > 0 else "—"
        tt_text = f"📅 {p['timestamp']}\n🎮 Plays: {p.get('play_count', '—')}\n⚡ Total OP: {p['op']:,.2f} / {p['max_op']:,.2f}\n📊 OP %: {p['pct']:.3f}%\n📈 Δ OP: {d_str}"

        tx = min(self.winfo_width() - 150, max(10, x + 12))
        ty = max(20, min(self.winfo_height() - 95, y - 65))
        self.create_rectangle(tx, ty, tx + 144, ty + 88, fill="#0f172a", outline=DARK_THEME["accent"], width=1, tags="tooltip")
        self.create_text(tx + 8, ty + 8, text=tt_text, fill="#f8fafc", font=("Helvetica", 8), anchor="nw", tags="tooltip")

class MaimaiOpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("maimai-op Dashboard")
        self.root.geometry("640x720")
        self.root.minsize(540, 480)
        self.root.configure(bg=DARK_THEME["bg_main"])
        set_windows_dark_titlebar(self.root)

        self.version_order = {v: i for i, v in enumerate(load_json("data/versions.json", []))}
        self.active_user_id = "kalta"
        self.available_profiles = []
        self.history_data = []
        self.all_summary = None
        self.rows_data = []
        self.level_rows_data = []
        self.header_bg_photo = None
        self.sort_state = {"column": "version", "descending": False}
        self.level_sort_state = {"column": "level", "descending": False}

        self.apply_theme()
        self.setup_ui()
        self.refresh_profiles()

    def get_user_dir(self, user_id):
        return Path(f"users/{user_id}")

    def apply_theme(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure("TFrame", background=DARK_THEME["bg_main"])
        s.configure("TLabel", background=DARK_THEME["bg_main"], foreground=DARK_THEME["text_primary"])
        s.configure("Header.TLabel", font=("Helvetica", 9, "bold"), foreground=DARK_THEME["text_primary"])
        s.configure("Status.TLabel", font=("Helvetica", 9), foreground=DARK_THEME["accent"])
        s.configure("TCombobox", fieldbackground=DARK_THEME["bg_input"], background=DARK_THEME["bg_card"], foreground=DARK_THEME["text_primary"])
        s.configure("TButton", background=DARK_THEME["bg_card"], foreground=DARK_THEME["text_primary"], bordercolor="#3b4252", padding=(6, 3))
        s.map("TButton", background=[("active", "#333842"), ("pressed", "#2d313b")])
        s.configure("TNotebook", background=DARK_THEME["bg_main"], borderwidth=0)
        s.configure("TNotebook.Tab", background=DARK_THEME["bg_card"], foreground=DARK_THEME["text_secondary"], padding=(10, 4), font=("Helvetica", 9, "bold"))
        s.map("TNotebook.Tab", background=[("selected", DARK_THEME["bg_input"])], foreground=[("selected", DARK_THEME["accent"])])
        s.configure("Treeview", background=DARK_THEME["tree_bg"], foreground=DARK_THEME["text_primary"], fieldbackground=DARK_THEME["tree_bg"], rowheight=24, font=("Helvetica", 9))
        s.configure("Treeview.Heading", background=DARK_THEME["tree_head_bg"], foreground=DARK_THEME["text_primary"], relief="flat", font=("Helvetica", 9, "bold"))
        s.configure("Vertical.TScrollbar", background=DARK_THEME["bg_card"], troughcolor=DARK_THEME["bg_main"], arrowcolor=DARK_THEME["text_secondary"])

    def setup_ui(self):
        bar = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="Profile:", style="Header.TLabel").pack(side="left", padx=(0, 4))

        self.profile_combo = ttk.Combobox(bar, state="readonly", width=16, font=("Helvetica", 9))
        self.profile_combo.pack(side="left", padx=(0, 6))
        self.profile_combo.bind("<<ComboboxSelected>>", lambda e: self.on_profile_selected())

        ttk.Button(bar, text="+ Add", command=self.add_new_profile).pack(side="left", padx=(0, 3))
        ttk.Button(bar, text="🔑 Sync SEGA Direct", command=self.trigger_sega_sync).pack(side="left", padx=(0, 3))
        ttk.Button(bar, text="⚡ Recalc", command=self.recalculate_active_user).pack(side="left")

        self.status_lbl = ttk.Label(bar, text="", style="Status.TLabel")
        self.status_lbl.pack(side="right")

        # Header Canvas
        self.header_canvas = tk.Canvas(self.root, height=86, bd=0, highlightthickness=0, bg=DARK_THEME["bg_main"])
        self.header_canvas.pack(fill="x", padx=10, pady=(4, 2))
        self.header_canvas.bind("<Configure>", lambda e: self.render_header_canvas())

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        # Table Tab (Versions)
        tab_t = ttk.Frame(self.notebook)
        self.notebook.add(tab_t, text="📋 Versions Table")
        self.columns = [
            ("version", "Version", 125, "w"),
            ("plate", "Plate", 70, "center"),
            ("version_op", "OP", 75, "e"),
            ("delta_op", "Δ OP", 58, "e"),
            ("version_max_op", "Max OP", 75, "e"),
            ("op_percent", "OP %", 62, "e"),
            ("delta_percent", "Δ %", 52, "e"),
        ]
        self.tree = ttk.Treeview(tab_t, columns=[c[0] for c in self.columns], show="headings", selectmode="browse")
        sb = ttk.Scrollbar(tab_t, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for c_id, title, w, anc in self.columns:
            self.tree.column(c_id, width=w, minwidth=40, anchor=anc)  # type: ignore
            self.tree.heading(c_id, text=title, command=lambda c=c_id: self.on_header_click(c))

        for p_lvl, col in PLATE_COLORS.items():
            if p_lvl > 0:
                hex_bg = f"#{col['bg'][0]:02x}{col['bg'][1]:02x}{col['bg'][2]:02x}"
                hex_fg = f"#{col['fg'][0]:02x}{col['fg'][1]:02x}{col['fg'][2]:02x}"
                self.tree.tag_configure(f"plate_{p_lvl}", background=hex_bg, foreground=hex_fg)
        self.tree.tag_configure("plate_0", background=DARK_THEME["tree_bg"], foreground=DARK_THEME["text_secondary"])

        # Levels Tab
        tab_l = ttk.Frame(self.notebook)
        self.notebook.add(tab_l, text="🎯 Levels Table")
        self.level_columns = [
            ("level", "Level", 85, "center"),
            ("plate", "Plate", 70, "center"),
            ("level_op", "OP", 75, "e"),
            ("delta_op", "Δ OP", 58, "e"),
            ("level_max_op", "Max OP", 75, "e"),
            ("op_percent", "OP %", 62, "e"),
            ("delta_percent", "Δ %", 52, "e"),
            ("progress", "Progress", 85, "center"),
        ]
        self.level_tree = ttk.Treeview(tab_l, columns=[c[0] for c in self.level_columns], show="headings", selectmode="browse")
        sb_l = ttk.Scrollbar(tab_l, orient="vertical", command=self.level_tree.yview)
        self.level_tree.configure(yscrollcommand=sb_l.set)
        self.level_tree.pack(side="left", fill="both", expand=True)
        sb_l.pack(side="right", fill="y")

        for c_id, title, w, anc in self.level_columns:
            self.level_tree.column(c_id, width=w, minwidth=40, anchor=anc)  # type: ignore
            self.level_tree.heading(c_id, text=title, command=lambda c=c_id: self.on_level_header_click(c))

        for p_lvl, col in PLATE_COLORS.items():
            if p_lvl > 0:
                hex_bg = f"#{col['bg'][0]:02x}{col['bg'][1]:02x}{col['bg'][2]:02x}"
                hex_fg = f"#{col['fg'][0]:02x}{col['fg'][1]:02x}{col['fg'][2]:02x}"
                self.level_tree.tag_configure(f"plate_{p_lvl}", background=hex_bg, foreground=hex_fg)
        self.level_tree.tag_configure("plate_0", background=DARK_THEME["tree_bg"], foreground=DARK_THEME["text_secondary"])

        # Graph Tab
        tab_g = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_g, text="📈 OP Growth Graph")
        stats_frame = tk.Frame(tab_g, bg=DARK_THEME["bg_card"], bd=1, relief="solid", padx=10, pady=6)
        stats_frame.pack(fill="x", pady=(0, 6))
        self.graph_stat_lbl = tk.Label(stats_frame, text="", font=("Helvetica", 9, "bold"), bg=DARK_THEME["bg_card"], fg=DARK_THEME["text_primary"])
        self.graph_stat_lbl.pack(side="left")
        self.history_graph = HistoryGraphCanvas(tab_g)
        self.history_graph.pack(fill="both", expand=True)

    def render_header_canvas(self):
        w = max(200, self.header_canvas.winfo_width())
        h = 86

        all_pos = self.all_summary.get("possession", 0) if self.all_summary else 0
        all_op = self.all_summary.get("version_op", 0.0) if self.all_summary else 0.0
        all_max = self.all_summary.get("version_max_op", 0.0) if self.all_summary else 0.0
        all_pct = self.all_summary.get("op_percent", 0.0) if self.all_summary else 0.0
        d_op = self.all_summary.get("delta_op", 0.0) if self.all_summary else 0.0
        d_pct = self.all_summary.get("delta_percent", 0.0) if self.all_summary else 0.0

        gradient_img = generate_gradient_badge(all_pos, width=w, height=h, radius=8)
        self.header_bg_photo = ImageTk.PhotoImage(gradient_img)
        self.header_canvas.delete("all")
        self.header_canvas.create_image(0, 0, image=self.header_bg_photo, anchor="nw")

        username, play_text, last_sync = self.active_user_id, "—", "—"
        if self.history_data:
            latest = self.history_data[-1]
            username = latest.get("username", self.active_user_id)
            tot_p = str(latest.get("play_count", ""))
            ver_p = str(latest.get("version_play_count", ""))
            if tot_p.isdigit():
                tot_str = f"{int(tot_p):,} plays"
                if ver_p.isdigit() and int(ver_p) != int(tot_p):
                    play_text = f"{tot_str}  ({int(ver_p):,} this version)"
                else:
                    play_text = tot_str
            else:
                play_text = "—"
            last_sync = latest.get("timestamp", "—")

        c_main = "#111827" if all_pos > 0 else "#f8fafc"
        c_sub = "#374151" if all_pos > 0 else "#94a3b8"
        c_acc = "#030712" if all_pos > 0 else "#e2e8f0"

        self.header_canvas.create_text(14, 18, text=f"Player: {username}  (@{self.active_user_id})", font=("Helvetica", 12, "bold"), fill=c_main, anchor="w")
        self.header_canvas.create_text(w - 14, 18, text=last_sync, font=("Helvetica", 8, "italic"), fill=c_sub, anchor="e")
        self.header_canvas.create_text(14, 40, text=f"Plays: {play_text}", font=("Helvetica", 9, "bold"), fill=c_sub, anchor="w")

        if self.all_summary:
            base_txt = f"Overpower: {all_op:,.2f} / {all_max:,.2f} "
            tag_id = self.header_canvas.create_text(14, 63, text=base_txt, font=("Helvetica", 9, "bold"), fill=c_acc, anchor="w")
            bbox = self.header_canvas.bbox(tag_id)
            pct_x = bbox[2] if bbox else 170
            pct_rgb = get_op_tier_color(all_pct)
            pct_hex = f"#{pct_rgb[0]:02x}{pct_rgb[1]:02x}{pct_rgb[2]:02x}"
            self.header_canvas.create_text(pct_x, 63, text=f"({all_pct:.3f}%)", font=("Helvetica", 9, "bold"), fill=pct_hex, anchor="w")

            if d_op != 0 or d_pct != 0:
                d_color = "#15803d" if d_op > 0 else "#b91c1c"
                self.header_canvas.create_text(w - 14, 63, text=f"(Δ {format_delta(d_op)} | {format_delta(d_pct, is_percent=True)})", font=("Helvetica", 9, "bold"), fill=d_color, anchor="e")
        else:
            self.header_canvas.create_text(14, 63, text="No calculated data yet. Click 'Sync SEGA Direct'.", font=("Helvetica", 8, "italic"), fill=c_sub, anchor="w")

    def refresh_profiles(self, select_user=None):
        users_dir = Path("users")
        users_dir.mkdir(exist_ok=True)
        profiles = []
        for d in users_dir.iterdir():
            if d.is_dir():
                h = load_json(d / "history.json", [])
                name = h[-1].get("username", d.name) if h else d.name
                profiles.append({"id": d.name, "name": name, "label": f"{name} (@{d.name})" if name != d.name else f"@{d.name}"})

        self.available_profiles = profiles or [{"id": "kalta", "name": "kalta", "label": "@kalta"}]
        self.profile_combo["values"] = [p["label"] for p in self.available_profiles]
        target = select_user or self.active_user_id
        idx = next((i for i, p in enumerate(self.available_profiles) if p["id"] == target), 0)
        self.profile_combo.current(idx)
        self.on_profile_selected()

    def on_profile_selected(self):
        idx = self.profile_combo.current()
        if 0 <= idx < len(self.available_profiles):
            self.active_user_id = self.available_profiles[idx]["id"]
            self.load_active_user_data()

    def load_active_user_data(self):
        self.history_data = load_json(self.get_user_dir(self.active_user_id) / "history.json", [])
        self.all_summary, self.rows_data, self.level_rows_data = None, [], []

        if self.history_data:
            latest = self.history_data[-1]
            for item in latest.get("data", []):
                v_op, v_max, d_op = float(item.get("version_op", 0)), float(item.get("version_max_op", 0)), float(item.get("delta_op", 0))
                pct = round((v_op / v_max * 100), 3 if item.get("version") == "ALL" else 2) if v_max > 0 else 0.0
                row = {
                    "version": item.get("version", ""), "possession": item.get("possession", 0),
                    "version_op": v_op, "version_max_op": v_max, "op_percent": pct,
                    "delta_op": d_op, "delta_percent": round((d_op / v_max * 100), 2) if v_max > 0 else 0.0
                }
                if item.get("version") == "ALL":
                    self.all_summary = row
                else:
                    self.rows_data.append(row)

            for item in latest.get("levels_data", []):
                l_op, l_max, d_op = float(item.get("level_op", 0)), float(item.get("level_max_op", 0)), float(item.get("delta_op", 0))
                pct = float(item.get("op_percent", 0))
                played = item.get("played_charts", 0)
                tot = item.get("total_charts", 0)
                lvl = str(item.get("level", ""))
                self.level_rows_data.append({
                    "level": f"Lv {lvl}",
                    "level_raw": lvl,
                    "possession": item.get("possession", 0),
                    "level_op": l_op,
                    "level_max_op": l_max,
                    "op_percent": pct,
                    "delta_op": d_op,
                    "delta_percent": round((d_op / l_max * 100), 2) if l_max > 0 else 0.0,
                    "progress": f"{played}/{tot} ({played/tot*100:.0f}%)" if tot > 0 else "—"
                })

        self.render_header_canvas()
        self.sort_rows(self.sort_state["column"], self.sort_state["descending"])
        self.sort_level_rows(self.level_sort_state["column"], self.level_sort_state["descending"])
        self.history_graph.set_data(self.history_data)

        if self.history_data:
            first, last = self.history_data[0].get("data", []), self.history_data[-1].get("data", [])
            f_op = next((i["version_op"] for i in first if i.get("version") == "ALL"), 0.0)
            l_op = next((i["version_op"] for i in last if i.get("version") == "ALL"), 0.0)
            gain = l_op - f_op
            self.graph_stat_lbl.config(text=f"📈 Timeline: {len(self.history_data)} Snapshots  |  Initial: {f_op:,.2f}  ➜  Current: {l_op:,.2f}  (Total: {'+' if gain > 0 else ''}{gain:,.2f} OP)")
        else:
            self.graph_stat_lbl.config(text="No historical snapshots logged.")

    def on_header_click(self, col_id):
        self.sort_state["descending"] = not self.sort_state["descending"] if self.sort_state["column"] == col_id else False
        self.sort_state["column"] = col_id
        self.sort_rows(col_id, self.sort_state["descending"])

    def sort_rows(self, col_id, descending):
        for c_id, title, _, _ in self.columns:
            self.tree.heading(c_id, text=f"{title}{' ▼' if descending else ' ▲'}" if c_id == col_id else title)

        def key_fn(item):
            if col_id == "version": return self.version_order.get(item.get("version"), 999)
            if col_id == "plate": return item.get("possession", 0)
            if col_id in ("version_op", "delta_op", "version_max_op", "op_percent", "delta_percent"): return float(item.get(col_id, 0))
            return str(item.get(col_id, "")).lower()

        self.rows_data.sort(key=key_fn, reverse=descending)
        for item in self.tree.get_children():
            self.tree.delete(item)

        for item in self.rows_data:
            pos = item.get("possession", 0)
            self.tree.insert("", "end", values=(
                item.get("version", ""), PLATE_NAMES.get(pos, "—"), f"{item.get('version_op', 0):,.2f}",
                format_delta(item.get("delta_op", 0)), f"{item.get('version_max_op', 0):,.2f}",
                f"{item.get('op_percent', 0):.2f}%", format_delta(item.get("delta_percent", 0), is_percent=True)
            ), tags=(f"plate_{pos}",))

    def on_level_header_click(self, col_id):
        self.level_sort_state["descending"] = not self.level_sort_state["descending"] if self.level_sort_state["column"] == col_id else False
        self.level_sort_state["column"] = col_id
        self.sort_level_rows(col_id, self.level_sort_state["descending"])

    def sort_level_rows(self, col_id, descending):
        for c_id, title, _, _ in self.level_columns:
            self.level_tree.heading(c_id, text=f"{title}{' ▼' if descending else ' ▲'}" if c_id == col_id else title)

        def key_fn(item):
            if col_id == "level": return level_sort_key(item.get("level_raw", ""))
            if col_id == "plate": return item.get("possession", 0)
            if col_id in ("level_op", "delta_op", "level_max_op", "op_percent", "delta_percent"): return float(item.get(col_id, 0))
            return str(item.get(col_id, "")).lower()

        self.level_rows_data.sort(key=key_fn, reverse=descending)
        for item in self.level_tree.get_children():
            self.level_tree.delete(item)

        for item in self.level_rows_data:
            pos = item.get("possession", 0)
            self.level_tree.insert("", "end", values=(
                item.get("level", ""), PLATE_NAMES.get(pos, "—"), f"{item.get('level_op', 0):,.2f}",
                format_delta(item.get("delta_op", 0)), f"{item.get('level_max_op', 0):,.2f}",
                f"{item.get('op_percent', 0):.2f}%", format_delta(item.get("delta_percent", 0), is_percent=True),
                item.get("progress", "—")
            ), tags=(f"plate_{pos}",))

    def add_new_profile(self):
        new_h = simpledialog.askstring("Add Profile", "Enter profile handle/ID:\n(e.g., your username)", parent=self.root)
        if not new_h or not new_h.strip():
            return
        handle = new_h.strip().lower()
        d = self.get_user_dir(handle)
        d.mkdir(parents=True, exist_ok=True)
        (d / "records").mkdir(exist_ok=True)
        self.refresh_profiles(select_user=handle)
        if messagebox.askyesno("Sync Profile", f"Profile '@{handle}' created!\n\nSync scores from SEGA DX NET now?"):
            self.trigger_sega_sync()

    def recalculate_active_user(self):
        self.status_lbl.config(text=f"Recalculating @{self.active_user_id}...")
        self.root.update_idletasks()
        try:
            calculate_for_user(self.active_user_id)
            self.load_active_user_data()
            self.status_lbl.config(text="Recalculation complete!")
        except Exception as e:
            self.status_lbl.config(text="Recalculation failed")
            messagebox.showerror("Error", f"Recalculation failed: {e}")

    def trigger_sega_sync(self):
        user_id = self.active_user_id
        tok_file = self.get_user_dir(user_id) / "auth_token.txt"
        saved = tok_file.read_text(encoding="utf-8").strip() if tok_file.exists() else ""
        if saved:
            self.start_sync_thread(user_id, saved)
        else:
            self.prompt_and_sync()

    def prompt_and_sync(self):
        user_id = self.active_user_id
        tok_file = self.get_user_dir(user_id) / "auth_token.txt"
        saved = tok_file.read_text(encoding="utf-8").strip() if tok_file.exists() else ""
        val = simpledialog.askstring("SEGA Sync", f"Enter your CLAL or _t token:\n(Profile: @{user_id})", initialvalue=saved, parent=self.root)
        if val:
            self.start_sync_thread(user_id, val.strip())

    def start_sync_thread(self, user_id, token_val):
        self.status_lbl.config(text="Connecting to SEGA DX NET...")
        self.root.update_idletasks()

        def worker():
            try:
                res = sync_sega_direct(user_id, token_val)
                self.root.after(0, lambda: self.on_sync_done(user_id, None, res))
            except Exception as e:
                self.root.after(0, lambda err=str(e): self.on_sync_done(user_id, err, None))

        threading.Thread(target=worker, daemon=True).start()

    def on_sync_done(self, user_id, err, res):
        if err:
            self.status_lbl.config(text="Sync failed")
            if messagebox.askyesno("Sync Error", f"Failed to sync with SEGA DX NET:\n\n{err}\n\nEnter a new CLAL token?"):
                self.prompt_and_sync()
        else:
            self.status_lbl.config(text="Sync complete!")
            self.refresh_profiles(select_user=user_id)
            messagebox.showinfo("Sync Success", f"Synced from SEGA DX NET!\n\nPlayer: {res['player_data']['username']}\nPlays: {int(res['player_data']['play_count']):,} plays\nUpdated {res['versions_count']} version records.")

def main():
    root = tk.Tk()
    app = MaimaiOpApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()