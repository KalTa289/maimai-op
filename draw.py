import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageDraw, ImageTk
import json
import threading
import asyncio
import ctypes
from pathlib import Path

PLATE_NAMES = {
    4: "Rainbow",
    3: "Platinum",
    2: "Gold",
    1: "Silver",
    0: "—"
}

PLATE_ROW_COLORS = {
    4: {"bg": "#f1daf9", "fg": "#250c38"},  # Prismatic lavender
    3: {"bg": "#ffe8a8", "fg": "#3b2b00"},  # Warm champagne gold
    2: {"bg": "#fcdc30", "fg": "#3b2b00"},  # Vivid lemon gold
    1: {"bg": "#76d9f7", "fg": "#04324a"},  # Sky cerulean cyan
}

DARK_THEME = {
    "bg_main": "#18191c",
    "bg_card": "#22252a",
    "bg_input": "#2a2d34",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "accent": "#38bdf8",
    "accent_glow": "#0284c7",
    "grid_line": "#2a2d34",
    "tree_bg": "#1e2024",
    "tree_head_bg": "#282b32",
}

def set_windows_dark_titlebar(root):
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass

def generate_header_gradient(plate_id, width=580, height=86):
    width = max(200, width)
    height = max(40, height)
    img = Image.new("RGB", (width, height), (24, 25, 28))

    if plate_id == 4:
        for y in range(height):
            for x in range(width):
                p = (x / width) * 0.70 + (y / height) * 0.30
                if p < 0.22:
                    r, g, b = int(248 + 7 * (p / 0.22)), int(225 + 30 * (1 - p / 0.22)), int(248 + 7 * (p / 0.22))
                elif p < 0.38:
                    t = (p - 0.22) / 0.16
                    r, g, b = int(248 * (1 - t) + 195 * t), int(175 * (1 - t) + 165 * t), int(235 * (1 - t) + 252 * t)
                elif p < 0.65:
                    t = (p - 0.38) / 0.27
                    r, g, b = int(195 * (1 - t) + 125 * t), int(165 * (1 - t) + 195 * t), int(252 * (1 - t) + 255 * t)
                else:
                    t = (p - 0.65) / 0.35
                    r, g, b = int(125 * (1 - t) + 135 * t), int(195 * (1 - t) + 245 * t), int(255 * (1 - t) + 175 * t)

                sheen_dist = abs((x - 1.5 * y) - (width * 0.30))
                if sheen_dist < 8:
                    sheen = (1 - sheen_dist / 8) * 35
                    r, g, b = min(255, int(r + sheen)), min(255, int(g + sheen)), min(255, int(b + sheen))

                img.putpixel((x, y), (r, g, b))

    elif plate_id == 3:
        for y in range(height):
            for x in range(width):
                t = x / width
                r, g, b = int(248 * (1 - t) + 255 * t), int(206 * (1 - t) + 246 * t), int(130 * (1 - t) + 192 * t)
                sheen_dist = abs((x - 1.5 * y) - (width * 0.38))
                if (x - 1.5 * y) > (width * 0.38):
                    r, g, b = min(255, int(r + 14)), min(255, int(g + 14)), min(255, int(b + 14))
                if sheen_dist < 6:
                    sheen = (1 - sheen_dist / 6) * 45
                    r, g, b = min(255, int(r + sheen)), min(255, int(g + sheen)), min(255, int(b + sheen))
                img.putpixel((x, y), (r, g, b))

    elif plate_id == 2:
        for y in range(height):
            for x in range(width):
                t = x / width
                r, g, b = int(225 * (1 - t) + 255 * t), int(160 * (1 - t) + 240 * t), int(10 * (1 - t) + 40 * t)
                sheen_dist = abs((x - 1.5 * y) - (width * 0.38))
                if (x - 1.5 * y) > (width * 0.38):
                    r, g, b = min(255, int(r + 16)), min(255, int(g + 16)), min(255, int(b + 16))
                if sheen_dist < 6:
                    sheen = (1 - sheen_dist / 6) * 50
                    r, g, b = min(255, int(r + sheen)), min(255, int(g + sheen)), min(255, int(b + sheen))
                img.putpixel((x, y), (r, g, b))

    elif plate_id == 1:
        for y in range(height):
            for x in range(width):
                t = x / width
                r, g, b = int(88 * (1 - t) + 155 * t), int(188 * (1 - t) + 235 * t), int(224 * (1 - t) + 255 * t)
                sheen_dist = abs((x - 1.5 * y) - (width * 0.38))
                if (x - 1.5 * y) > (width * 0.38):
                    r, g, b = min(255, int(r + 16)), min(255, int(g + 16)), min(255, int(b + 16))
                if sheen_dist < 6:
                    sheen = (1 - sheen_dist / 6) * 45
                    r, g, b = min(255, int(r + sheen)), min(255, int(g + sheen)), min(255, int(b + sheen))
                img.putpixel((x, y), (r, g, b))
    else:
        for y in range(height):
            for x in range(width):
                t = x / width
                r, g, b = int(38 * (1 - t) + 48 * t), int(42 * (1 - t) + 54 * t), int(50 * (1 - t) + 62 * t)
                img.putpixel((x, y), (r, g, b))

    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=8, fill=255)

    rounded_img = Image.new("RGB", (width, height), (24, 25, 28))
    rounded_img.paste(img, (0, 0), mask=mask)

    draw_final = ImageDraw.Draw(rounded_img)
    outline_color = (0, 0, 0, 120) if plate_id > 0 else (60, 68, 80)
    draw_final.rounded_rectangle([0, 0, width - 1, height - 1], radius=8, outline=outline_color, width=1)

    return rounded_img

def load_json(path, default=None):
    if default is None:
        default = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

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
        self.bind("<Leave>", lambda e: self.hide_tooltip())

    def set_data(self, history_snapshots):
        self.points = []
        for snap in history_snapshots:
            ts = snap.get("timestamp", "")
            plays = snap.get("play_count", "")
            all_item = next((item for item in snap.get("data", []) if item.get("version") == "ALL"), None)
            if all_item:
                op = float(all_item.get("version_op", 0.0))
                max_op = float(all_item.get("version_max_op", 0.0))
                pct = (op / max_op * 100) if max_op > 0 else 0.0
                self.points.append({
                    "timestamp": ts,
                    "play_count": plays,
                    "op": op,
                    "max_op": max_op,
                    "pct": pct
                })
        self.draw_graph()

    def draw_graph(self):
        self.delete("all")
        self.dot_coords = []
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 100 or h < 80:
            return

        if not self.points:
            self.create_text(w // 2, h // 2, text="No historical snapshots recorded yet.", fill=DARK_THEME["text_secondary"], font=("Helvetica", 11))
            return

        pad_left = 65
        pad_right = 35
        pad_top = 35
        pad_bottom = 45

        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        ops = [p["op"] for p in self.points]
        min_op = min(ops)
        max_op = max(ops)

        if max_op == min_op:
            y_min = max(0, min_op - 50)
            y_max = max_op + 50
        else:
            margin = max(10.0, (max_op - min_op) * 0.20)
            y_min = max(0, min_op - margin)
            y_max = max_op + margin

        # Draw Grid Lines
        for i in range(5):
            y_val = y_min + (y_max - y_min) * (i / 4)
            y_pos = pad_top + plot_h - (i / 4) * plot_h
            self.create_line(pad_left, y_pos, w - pad_right, y_pos, fill=DARK_THEME["grid_line"], dash=(3, 3))
            self.create_text(pad_left - 8, y_pos, text=f"{y_val:,.0f}", fill=DARK_THEME["text_secondary"], font=("Helvetica", 8), anchor="e")

        n = len(self.points)
        coords = []
        for i, p in enumerate(self.points):
            x = (pad_left + plot_w / 2) if n == 1 else pad_left + (i / (n - 1)) * plot_w
            y_ratio = (p["op"] - y_min) / (y_max - y_min) if (y_max > y_min) else 0.5
            y = pad_top + plot_h - (y_ratio * plot_h)
            coords.append((x, y))
            self.dot_coords.append((x, y, p, i))

            # X-axis label
            short_ts = p["timestamp"][5:16] if len(p["timestamp"]) >= 16 else p["timestamp"]
            label_text = f"#{p['play_count']}" if p.get("play_count") else short_ts
            self.create_text(x, h - pad_bottom + 14, text=label_text, fill=DARK_THEME["text_secondary"], font=("Helvetica", 8), anchor="center")

        # Draw Gradient Shaded Area
        if len(coords) >= 2:
            poly_points = [coords[0][0], pad_top + plot_h]
            for cx, cy in coords:
                poly_points.extend([cx, cy])
            poly_points.extend([coords[-1][0], pad_top + plot_h])
            self.create_polygon(poly_points, fill="#0f2942", outline="")

            # Draw Connecting Neon Line
            flat_coords = []
            for cx, cy in coords:
                flat_coords.extend([cx, cy])
            self.create_line(flat_coords, fill=DARK_THEME["accent"], width=3, smooth=(n > 2))

        # Draw Point Dots & Values
        for x, y, p, idx in self.dot_coords:
            self.create_oval(x - 5, y - 5, x + 5, y + 5, fill=DARK_THEME["accent"], outline="#ffffff", width=2)
            self.create_text(x, y - 12, text=f"{p['op']:,.1f}", fill=DARK_THEME["text_primary"], font=("Helvetica", 8, "bold"))

    def on_mouse_move(self, event):
        mx, my = event.x, event.y
        closest = None
        min_dist = 22
        for x, y, p, idx in self.dot_coords:
            dist = ((mx - x) ** 2 + (my - y) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest = (x, y, p, idx)

        if closest:
            self.show_tooltip(closest[0], closest[1], closest[2], closest[3])
        else:
            self.hide_tooltip()

    def show_tooltip(self, x, y, p, idx):
        self.delete("tooltip")
        delta_str = "—"
        if idx > 0:
            prev_op = self.points[idx - 1]["op"]
            diff = p["op"] - prev_op
            sign = "+" if diff > 0 else ""
            delta_str = f"{sign}{diff:,.2f}"

        tt_lines = [
            f"📅 {p['timestamp']}",
            f"🎮 Plays: {p.get('play_count', '—')}",
            f"⚡ Total OP: {p['op']:,.2f} / {p['max_op']:,.2f}",
            f"📊 OP %: {p['pct']:.3f}%",
            f"📈 Δ OP: {delta_str}"
        ]
        tt_text = "\n".join(tt_lines)

        tx = min(self.winfo_width() - 150, max(10, x + 12))
        ty = max(20, min(self.winfo_height() - 95, y - 65))

        self.create_rectangle(tx, ty, tx + 144, ty + 88, fill="#0f172a", outline=DARK_THEME["accent"], width=1, tags="tooltip")
        self.create_text(tx + 8, ty + 8, text=tt_text, fill="#f8fafc", font=("Helvetica", 8), anchor="nw", tags="tooltip")

    def hide_tooltip(self):
        self.delete("tooltip")

class MaimaiOpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("maimai-op Dashboard")
        self.root.geometry("620x720")
        self.root.minsize(540, 480)
        self.root.configure(bg=DARK_THEME["bg_main"])

        # Enable Windows dark titlebar
        set_windows_dark_titlebar(self.root)

        # Global version order mapping from data/versions.json
        self.raw_versions = load_json("data/versions.json", [])
        self.version_order = {v: i for i, v in enumerate(self.raw_versions)}

        # Active user profile state
        self.active_user_id = "kalta"
        self.available_profiles = []
        self.history_data = []
        self.all_summary = None
        self.rows_data = []

        # Header background photo reference
        self.header_bg_photo = None

        # Sorting state: (column_name, is_descending)
        self.sort_state = {"column": "version", "descending": False}

        self.apply_theme_styles()
        self.setup_ui()
        self.refresh_profiles()

    def get_user_dir(self, user_id):
        return Path(f"users/{user_id}")

    def apply_theme_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("TFrame", background=DARK_THEME["bg_main"])
        style.configure("TLabel", background=DARK_THEME["bg_main"], foreground=DARK_THEME["text_primary"])
        style.configure("Header.TLabel", font=("Helvetica", 9, "bold"), foreground=DARK_THEME["text_primary"])
        style.configure("Status.TLabel", font=("Helvetica", 9), foreground=DARK_THEME["accent"])

        style.configure("TCombobox", fieldbackground=DARK_THEME["bg_input"], background=DARK_THEME["bg_card"], foreground=DARK_THEME["text_primary"], darkcolor=DARK_THEME["bg_card"], lightcolor=DARK_THEME["bg_card"])

        style.configure("TButton", background=DARK_THEME["bg_card"], foreground=DARK_THEME["text_primary"], bordercolor="#3b4252", lightcolor=DARK_THEME["bg_card"], darkcolor=DARK_THEME["bg_card"], padding=(6, 2))
        style.map("TButton", background=[("active", "#333842"), ("pressed", "#2d313b")])

        # Dark Notebook Tabs
        style.configure("TNotebook", background=DARK_THEME["bg_main"], borderwidth=0)
        style.configure("TNotebook.Tab", background=DARK_THEME["bg_card"], foreground=DARK_THEME["text_secondary"], padding=(10, 4), font=("Helvetica", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", DARK_THEME["bg_input"]), ("active", "#333842")], foreground=[("selected", DARK_THEME["accent"]), ("active", DARK_THEME["text_primary"])])

        # Dark Treeview
        style.configure(
            "Treeview",
            background=DARK_THEME["tree_bg"],
            foreground=DARK_THEME["text_primary"],
            fieldbackground=DARK_THEME["tree_bg"],
            rowheight=24,
            font=("Helvetica", 9)
        )
        style.configure(
            "Treeview.Heading",
            background=DARK_THEME["tree_head_bg"],
            foreground=DARK_THEME["text_primary"],
            relief="flat",
            font=("Helvetica", 9, "bold")
        )
        style.map("Treeview.Heading", background=[("active", "#383d47")])

        style.configure("Vertical.TScrollbar", background=DARK_THEME["bg_card"], troughcolor=DARK_THEME["bg_main"], bordercolor=DARK_THEME["bg_main"], arrowcolor=DARK_THEME["text_secondary"])

    def setup_ui(self):
        # 1. Top Profile & Actions Bar
        profile_bar = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        profile_bar.pack(fill="x")

        ttk.Label(profile_bar, text="Profile:", style="Header.TLabel").pack(side="left", padx=(0, 6))

        self.profile_combo = ttk.Combobox(profile_bar, state="readonly", width=18, font=("Helvetica", 9))
        self.profile_combo.pack(side="left", padx=(0, 6))
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_selected)

        add_btn = ttk.Button(profile_bar, text="+ Add", command=self.add_new_profile)
        add_btn.pack(side="left", padx=(0, 4))

        sync_btn = ttk.Button(profile_bar, text="🔄 Sync", command=self.sync_active_user)
        sync_btn.pack(side="left", padx=(0, 4))

        calc_btn = ttk.Button(profile_bar, text="⚡ Recalc", command=self.recalculate_active_user)
        calc_btn.pack(side="left")

        self.status_lbl = ttk.Label(profile_bar, text="", style="Status.TLabel")
        self.status_lbl.pack(side="right")

        # 2. Integrated Gradient Header Canvas
        self.header_canvas_frame = ttk.Frame(self.root, padding=(10, 4, 10, 4))
        self.header_canvas_frame.pack(fill="x")

        self.header_canvas = tk.Canvas(self.header_canvas_frame, height=86, bd=0, highlightthickness=0, bg=DARK_THEME["bg_main"])
        self.header_canvas.pack(fill="x", expand=True)
        self.header_canvas.bind("<Configure>", self.on_header_canvas_resize)

        # 3. Tabbed View Switcher (Table vs OP Growth Graph)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        # Tab 1: Version Table
        table_tab = ttk.Frame(self.notebook)
        self.notebook.add(table_tab, text="📋 Versions Table")

        self.columns = [
            ("version", "Version", 125, "w"),
            ("plate", "Plate", 70, "center"),
            ("version_op", "OP", 75, "e"),
            ("delta_op", "Δ OP", 58, "e"),
            ("version_max_op", "Max OP", 75, "e"),
            ("op_percent", "OP %", 62, "e"),
            ("delta_percent", "Δ %", 52, "e"),
        ]

        self.tree = ttk.Treeview(
            table_tab,
            columns=[col[0] for col in self.columns],
            show="headings",
            selectmode="browse"
        )

        scrollbar = ttk.Scrollbar(table_tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for col_id, title, width, anchor in self.columns:
            self.tree.column(col_id, width=width, minwidth=40, anchor=anchor)
            self.tree.heading(col_id, text=title, command=lambda c=col_id: self.on_header_click(c))

        for plate_level, col_spec in PLATE_ROW_COLORS.items():
            self.tree.tag_configure(f"plate_{plate_level}", background=col_spec["bg"], foreground=col_spec["fg"])
        self.tree.tag_configure("plate_0", background=DARK_THEME["tree_bg"], foreground=DARK_THEME["text_secondary"])

        # Tab 2: OP Growth Graph
        graph_tab = ttk.Frame(self.notebook, padding=(6, 6, 6, 6))
        self.notebook.add(graph_tab, text="📈 OP Growth Graph")

        # Graph Highlights Stat Bar
        self.graph_stats_frame = tk.Frame(graph_tab, bg=DARK_THEME["bg_card"], bd=1, relief="solid", padx=10, pady=6)
        self.graph_stats_frame.pack(fill="x", pady=(0, 6))

        self.graph_stat_lbl = tk.Label(self.graph_stats_frame, text="", font=("Helvetica", 9, "bold"), bg=DARK_THEME["bg_card"], fg=DARK_THEME["text_primary"])
        self.graph_stat_lbl.pack(side="left")

        # Graph Canvas
        self.history_graph = HistoryGraphCanvas(graph_tab)
        self.history_graph.pack(fill="both", expand=True)

        # 4. Footer Status Bar
        footer = ttk.Frame(self.root, padding=(10, 2, 10, 6))
        footer.pack(fill="x", side="bottom")
        tip_lbl = ttk.Label(footer, text="💡 Tip: Switch tabs above to toggle between the Breakdown Table and the OP Growth Graph.", font=("Helvetica", 8, "italic"), foreground=DARK_THEME["text_secondary"])
        tip_lbl.pack(side="left")

    def on_header_canvas_resize(self, event=None):
        self.render_header_canvas()

    def render_header_canvas(self):
        w = self.header_canvas.winfo_width()
        h = 86
        if w < 100:
            w = 600

        all_pos = 0
        all_op = 0.0
        all_max = 0.0
        all_pct = 0.0
        delta_op = 0.0
        delta_pct = 0.0

        if self.all_summary:
            all_pos = self.all_summary.get("possession", 0)
            all_op = self.all_summary.get("version_op", 0.0)
            all_max = self.all_summary.get("version_max_op", 0.0)
            all_pct = self.all_summary.get("op_percent", 0.0)
            delta_op = self.all_summary.get("delta_op", 0.0)
            delta_pct = self.all_summary.get("delta_percent", 0.0)

        gradient_img = generate_header_gradient(all_pos, width=w, height=h)
        self.header_bg_photo = ImageTk.PhotoImage(gradient_img)

        self.header_canvas.delete("all")
        self.header_canvas.create_image(0, 0, image=self.header_bg_photo, anchor="nw")

        username = self.active_user_id
        play_count = "—"
        last_sync = "—"

        if self.history_data:
            latest = self.history_data[-1]
            username = latest.get("username", self.active_user_id)
            play_count = latest.get("play_count", "—")
            last_sync = latest.get("timestamp", "—")

        if str(play_count).isdigit():
            play_count = f"{int(play_count):,} plays"

        plate_str = PLATE_NAMES.get(all_pos, "—")

        text_color_primary = "#111827" if all_pos > 0 else "#f8fafc"
        text_color_secondary = "#374151" if all_pos > 0 else "#94a3b8"
        text_color_accent = "#030712" if all_pos > 0 else "#e2e8f0"

        # Line 1: Player Name & Handle + Snapshot Date
        self.header_canvas.create_text(14, 18, text=f"Player: {username}  (@{self.active_user_id})", font=("Helvetica", 12, "bold"), fill=text_color_primary, anchor="w")
        self.header_canvas.create_text(w - 14, 18, text=f"{last_sync}", font=("Helvetica", 8, "italic"), fill=text_color_secondary, anchor="e")

        # Line 2: Play count & Overall Plate
        self.header_canvas.create_text(14, 40, text=f"Plays: {play_count}   •   Overall Plate: {plate_str}", font=("Helvetica", 9, "bold"), fill=text_color_secondary, anchor="w")

        # Line 3: Total Overpower & Deltas
        if self.all_summary:
            op_text = f"Overpower: {all_op:,.2f} / {all_max:,.2f} ({all_pct:.3f}%)"
            self.header_canvas.create_text(14, 63, text=op_text, font=("Helvetica", 9, "bold"), fill=text_color_accent, anchor="w")

            if delta_op != 0 or delta_pct != 0:
                delta_str = format_delta(delta_op)
                delta_color = "#15803d" if delta_op > 0 else "#b91c1c"
                d_text = f"(Δ {delta_str} | {format_delta(delta_pct, is_percent=True)})"
                self.header_canvas.create_text(w - 14, 63, text=d_text, font=("Helvetica", 9, "bold"), fill=delta_color, anchor="e")
        else:
            self.header_canvas.create_text(14, 63, text="No calculated version data yet. Click 'Sync' or 'Recalc'.", font=("Helvetica", 8, "italic"), fill=text_color_secondary, anchor="w")

    def refresh_profiles(self, select_user=None):
        users_dir = Path("users")
        users_dir.mkdir(exist_ok=True)

        profiles = []
        for d in users_dir.iterdir():
            if d.is_dir():
                user_id = d.name
                h_data = load_json(d / "history.json", [])
                display_name = h_data[-1].get("username", user_id) if h_data else user_id
                profiles.append({
                    "id": user_id,
                    "name": display_name,
                    "label": f"{display_name} (@{user_id})" if display_name != user_id else f"@{user_id}"
                })

        if not profiles:
            profiles = [{"id": "kalta", "name": "kalta", "label": "@kalta"}]

        self.available_profiles = profiles
        labels = [p["label"] for p in profiles]
        self.profile_combo["values"] = labels

        target_id = select_user or self.active_user_id
        matched_idx = 0
        for i, p in enumerate(profiles):
            if p["id"] == target_id:
                matched_idx = i
                break

        self.profile_combo.current(matched_idx)
        self.on_profile_selected()

    def on_profile_selected(self, event=None):
        idx = self.profile_combo.current()
        if idx >= 0 and idx < len(self.available_profiles):
            self.active_user_id = self.available_profiles[idx]["id"]
            self.load_active_user_data()

    def load_active_user_data(self):
        user_dir = self.get_user_dir(self.active_user_id)
        self.history_data = load_json(user_dir / "history.json", [])

        self.all_summary = None
        self.rows_data = []

        if self.history_data:
            latest_snapshot = self.history_data[-1]
            raw_items = latest_snapshot.get("data", [])

            for item in raw_items:
                v_name = item.get("version", "")
                v_op = float(item.get("version_op", 0.0))
                v_max = float(item.get("version_max_op", 0.0))
                pos = item.get("possession", 0)
                d_op = float(item.get("delta_op", 0.0))

                op_pct = round((v_op / v_max * 100), 2) if v_max > 0 else 0.0
                d_pct = round((d_op / v_max * 100), 2) if v_max > 0 else 0.0

                row_dict = {
                    "version": v_name,
                    "possession": pos,
                    "version_op": v_op,
                    "version_max_op": v_max,
                    "op_percent": op_pct,
                    "delta_op": d_op,
                    "delta_percent": d_pct,
                }

                if v_name == "ALL":
                    row_dict["op_percent"] = round((v_op / v_max * 100), 3) if v_max > 0 else 0.0
                    self.all_summary = row_dict
                else:
                    self.rows_data.append(row_dict)

        self.render_header_canvas()
        self.sort_rows(self.sort_state["column"], self.sort_state["descending"])

        # Update History Graph
        self.history_graph.set_data(self.history_data)
        self.update_graph_stats()

    def update_graph_stats(self):
        if not self.history_data:
            self.graph_stat_lbl.config(text="No historical snapshots logged.")
            return

        n_snaps = len(self.history_data)
        first_all = next((item for item in self.history_data[0].get("data", []) if item.get("version") == "ALL"), None)
        last_all = next((item for item in self.history_data[-1].get("data", []) if item.get("version") == "ALL"), None)

        if first_all and last_all:
            first_op = first_all.get("version_op", 0.0)
            last_op = last_all.get("version_op", 0.0)
            total_gain = last_op - first_op
            gain_sign = "+" if total_gain > 0 else ""
            stat_text = f"📈 Timeline: {n_snaps} Snapshots  |  Initial: {first_op:,.2f}  ➜  Current: {last_op:,.2f}  (Total: {gain_sign}{total_gain:,.2f} OP)"
            self.graph_stat_lbl.config(text=stat_text)
        else:
            self.graph_stat_lbl.config(text=f"📈 Timeline: {n_snaps} Snapshots recorded")

    def on_header_click(self, col_id):
        if self.sort_state["column"] == col_id:
            self.sort_state["descending"] = not self.sort_state["descending"]
        else:
            self.sort_state["column"] = col_id
            self.sort_state["descending"] = False

        self.sort_rows(col_id, self.sort_state["descending"])

    def sort_rows(self, col_id, descending):
        for c_id, title, _, _ in self.columns:
            if c_id == col_id:
                indicator = " ▼" if descending else " ▲"
                self.tree.heading(c_id, text=f"{title}{indicator}")
            else:
                self.tree.heading(c_id, text=title)

        def get_sort_key(item):
            if col_id == "version":
                v_name = item.get("version", "")
                return self.version_order.get(v_name, 999)
            elif col_id == "plate":
                return item.get("possession", 0)
            elif col_id in ("version_op", "delta_op", "version_max_op", "op_percent", "delta_percent"):
                return float(item.get(col_id, 0.0) or 0.0)
            else:
                return str(item.get(col_id, "")).lower()

        self.rows_data.sort(key=get_sort_key, reverse=descending)
        self.populate_table()

    def populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for item in self.rows_data:
            pos = item.get("possession", 0)
            v_op = item.get("version_op", 0.0)
            d_op = item.get("delta_op", 0.0)
            v_max = item.get("version_max_op", 0.0)
            op_pct = item.get("op_percent", 0.0)
            d_pct = item.get("delta_percent", 0.0)

            plate_label = PLATE_NAMES.get(pos, "—")
            row_tag = f"plate_{pos}" if pos in (1, 2, 3, 4) else "plate_0"

            self.tree.insert(
                "",
                "end",
                values=(
                    item.get("version", ""),
                    plate_label,
                    f"{v_op:,.2f}",
                    format_delta(d_op),
                    f"{v_max:,.2f}",
                    f"{op_pct:.2f}%",
                    format_delta(d_pct, is_percent=True),
                ),
                tags=(row_tag,)
            )

    def add_new_profile(self):
        new_handle = simpledialog.askstring(
            "Add User Profile",
            "Enter the Maishift profile handle/ID:\n(e.g., the handle in maimai.shiftpsh.com/en/profile/<handle>)",
            parent=self.root
        )
        if not new_handle:
            return
        
        clean_handle = new_handle.strip().lower()
        if not clean_handle:
            return

        user_dir = self.get_user_dir(clean_handle)
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "records").mkdir(exist_ok=True)

        self.refresh_profiles(select_user=clean_handle)
        
        do_sync = messagebox.askyesno(
            "Sync Profile",
            f"Profile '@{clean_handle}' created!\n\nWould you like to sync play records from Maishift now?"
        )
        if do_sync:
            self.sync_active_user()

    def recalculate_active_user(self):
        from calculate import calculate_for_user
        self.status_lbl.config(text=f"Recalculating @{self.active_user_id}...")
        self.root.update_idletasks()
        try:
            calculate_for_user(self.active_user_id)
            self.load_active_user_data()
            self.status_lbl.config(text="Recalculation complete!")
        except Exception as e:
            self.status_lbl.config(text="Recalculation failed")
            messagebox.showerror("Error", f"Recalculation failed: {e}")

    def sync_active_user(self):
        user_id = self.active_user_id
        self.status_lbl.config(text=f"Syncing @{user_id}...")

        def run_thread():
            try:
                from sync import run_sync
                asyncio.run(run_sync(user_id))
                self.root.after(0, lambda: self.on_sync_finished(user_id, None))
            except Exception as e:
                self.root.after(0, lambda: self.on_sync_finished(user_id, str(e)))

        t = threading.Thread(target=run_thread, daemon=True)
        t.start()

    def on_sync_finished(self, user_id, err):
        if err:
            self.status_lbl.config(text="Sync failed")
            messagebox.showerror("Sync Error", f"Failed to sync @{user_id}:\n{err}")
        else:
            self.status_lbl.config(text="Sync complete!")
            self.refresh_profiles(select_user=user_id)

def main():
    root = tk.Tk()
    app = MaimaiOpApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()