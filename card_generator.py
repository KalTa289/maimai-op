import io
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. Colors, Palettes & Constants
# ==========================================

PLATE_COLORS = {
    4: {"bg": (241, 218, 249), "fg": (37, 12, 56), "name": "Rainbow"},
    3: {"bg": (255, 232, 168), "fg": (59, 43, 0), "name": "Platinum"},
    2: {"bg": (252, 220, 48), "fg": (59, 43, 0), "name": "Gold"},
    1: {"bg": (118, 217, 247), "fg": (4, 50, 74), "name": "Silver"},
    0: {"bg": (30, 32, 36), "fg": (148, 163, 184), "name": "—"}
}
PLATE_NAMES = {k: v["name"] for k, v in PLATE_COLORS.items()}
PLATE_EMOJIS = {4: "🌈", 3: "👑", 2: "🥇", 1: "🥈", 0: "⬜"}

GRADIENT_STOPS = {
    4: [(255, 230, 255), (248, 180, 235), (195, 165, 252), (130, 215, 255)],
    3: [(248, 210, 135), (255, 246, 195)],
    2: [(230, 170, 15), (255, 242, 45)],
    1: [(90, 190, 226), (160, 238, 255)],
    0: [(32, 35, 44), (42, 48, 56)],
}

DARK_BG = (24, 25, 28)
TEXT_WHITE = (241, 245, 249)
TEXT_MUTED = (148, 163, 184)
ACCENT_CYAN = (56, 189, 248)
GRID_LINE = (42, 45, 52)

LEVELS_ORDER = [
    "1", "2", "3", "4", "5", "6",
    "7", "7+", "8", "8+", "9", "9+",
    "10", "10+", "11", "11+", "12", "12+",
    "13", "13+", "14", "14+", "15"
]

# ==========================================
# 2. Font & Drawing Utilities
# ==========================================

def get_font(size: int, bold: bool = False):
    font_candidates = [
        "meiryob.ttc" if bold else "meiryo.ttc",
        "YuGothB.ttc" if bold else "YuGothM.ttc",
        "msgothic.ttc",
        "malgunbd.ttf" if bold else "malgun.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf"
    ]
    for f in font_candidates:
        try:
            return ImageFont.truetype(f, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()

def draw_text_outline(draw: ImageDraw.ImageDraw, pos, text: str, font, fill, outline=(0, 0, 0), outline_width: int = 1, anchor: str | None = None):
    x, y = pos
    if outline_width > 0:
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, fill=outline, font=font, anchor=anchor)
    draw.text((x, y), text, fill=fill, font=font, anchor=anchor)

def get_op_tier_color(pct: float) -> tuple[int, int, int]:
    """
    Returns text color matching the OP% threshold tier:
    >= 97.0%: Rainbow (Prismatic Lavender)
    >= 95.0%: Platinum (Light Champagne Bright Yellow)
    >= 93.0%: Gold (Vivid Lemon Gold)
    >= 90.0%: Silver (Sky Cerulean Cyan)
    <  90.0%: Neutral Slate
    """
    if pct >= 97.0:
        return (235, 140, 255)
    if pct >= 95.0:
        return (255, 242, 170)
    if pct >= 93.0:
        return (250, 204, 21)
    if pct >= 90.0:
        return (56, 189, 248)
    return (160, 175, 195)

def generate_gradient_badge(plate_id: int, width: int, height: int, radius: int = 6) -> Image.Image:
    width, height = max(20, width), max(10, height)
    stops = GRADIENT_STOPS.get(plate_id, GRADIENT_STOPS[0])
    strip = Image.new("RGB", (len(stops), 1))
    for i, color in enumerate(stops):
        strip.putpixel((i, 0), color)
    gradient = strip.resize((width, height), Image.Resampling.BILINEAR)

    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)

    rounded = Image.new("RGB", (width, height), DARK_BG)
    rounded.paste(gradient, (0, 0), mask=mask)
    outline_col = (0, 0, 0, 90) if plate_id > 0 else (60, 66, 78)
    ImageDraw.Draw(rounded).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, outline=outline_col, width=1)
    return rounded

def _draw_card_header(img: Image.Image, latest_snapshot: dict, width: int = 840):
    username = latest_snapshot.get("username", "Unknown")
    play_count = str(latest_snapshot.get("play_count", "—"))
    v_play_count = str(latest_snapshot.get("version_play_count", ""))
    if play_count.isdigit():
        tot_str = f"{int(play_count):,} plays"
        if v_play_count.isdigit() and int(v_play_count) != int(play_count):
            play_text = f"Plays: {tot_str}  ({int(v_play_count):,} this version)"
        else:
            play_text = f"Plays: {tot_str}"
    else:
        play_text = f"Plays: {play_count}"

    timestamp = latest_snapshot.get("timestamp", "—")
    all_row = next((item for item in latest_snapshot.get("data", []) if item.get("version") == "ALL"), None)
    all_pos = all_row.get("possession", 0) if all_row else 0
    all_op = float(all_row.get("version_op", 0.0)) if all_row else 0.0
    all_max = float(all_row.get("version_max_op", 0.0)) if all_row else 0.0
    all_pct = (all_op / all_max * 100) if all_max > 0 else 0.0
    all_d_op = float(all_row.get("delta_op", 0.0)) if all_row else 0.0

    banner_h = 100
    banner_img = generate_gradient_badge(all_pos, width=width - 32, height=banner_h, radius=10)
    img.paste(banner_img, (16, 16))

    banner_draw = ImageDraw.Draw(img)
    text_dark = (all_pos > 0)
    col_main = (17, 24, 39) if text_dark else (248, 250, 252)
    col_sub = (55, 65, 81) if text_dark else (148, 163, 184)
    col_accent = (3, 7, 18) if text_dark else (226, 232, 240)

    f_title = get_font(19, bold=True)
    f_sub = get_font(13, bold=True)
    f_stat = get_font(14, bold=True)
    f_small = get_font(11, bold=False)

    banner_draw.text((32, 30), f"Player: {username}", fill=col_main, font=f_title)
    banner_draw.text((width - 40, 32), f"{timestamp}", fill=col_sub, font=f_small, anchor="ra")
    banner_draw.text((32, 58), play_text, fill=col_sub, font=f_sub)

    op_base_text = f"Overpower: {all_op:,.2f} / {all_max:,.2f} "
    banner_draw.text((32, 82), op_base_text, fill=col_accent, font=f_stat)

    bbox = banner_draw.textbbox((32, 82), op_base_text, font=f_stat)
    pct_x = bbox[2]
    all_pct_col = get_op_tier_color(all_pct)
    draw_text_outline(banner_draw, (pct_x, 82), f"({all_pct:.3f}%)", f_stat, fill=all_pct_col, outline=(0, 0, 0), outline_width=1)

    if abs(all_d_op) > 0.001:
        d_sign = "+" if all_d_op > 0 else ""
        d_col = (21, 128, 61) if all_d_op > 0 else (185, 28, 28)
        banner_draw.text((width - 40, 82), f"(Δ {d_sign}{all_d_op:,.2f} OP)", fill=d_col, font=f_stat, anchor="ra")

# ==========================================
# 3. Card Image Generators
# ==========================================

def generate_profile_card(latest_snapshot: dict) -> io.BytesIO:
    """
    Renders an 840x560 dark mode profile card with gradient banner and 27-version grid.
    """
    width, height = 840, 560
    img = Image.new("RGB", (width, height), DARK_BG)
    _draw_card_header(img, latest_snapshot, width)
    draw = ImageDraw.Draw(img)

    versions_data = [item for item in latest_snapshot.get("data", []) if item.get("version") != "ALL"]
    cols, rows = 3, 9
    card_margin_x = 16
    start_y = 130
    grid_w = width - (card_margin_x * 2)
    col_w = (grid_w - (10 * (cols - 1))) // cols
    row_h = 42

    f_v_name = get_font(12, bold=True)
    f_v_op = get_font(11, bold=False)
    f_badge = get_font(11, bold=True)

    cell_templates = {p_id: generate_gradient_badge(p_id, col_w, row_h, radius=6) for p_id in range(5)}

    for i, v_item in enumerate(versions_data):
        c, r = i % cols, i // cols
        vx = card_margin_x + c * (col_w + 10)
        vy = start_y + r * (row_h + 5)

        pos = v_item.get("possession", 0)
        v_name = v_item.get("version", "")
        v_op = float(v_item.get("version_op", 0.0))
        v_max = float(v_item.get("version_max_op", 0.0))
        v_pct = (v_op / v_max * 100) if v_max > 0 else 0.0

        p_info = PLATE_COLORS.get(pos, PLATE_COLORS[0])
        img.paste(cell_templates[pos], (vx, vy))

        cell_fg = p_info["fg"] if pos > 0 else TEXT_MUTED
        pct_color = get_op_tier_color(v_pct)

        draw.text((vx + 10, vy + 8), v_name, fill=cell_fg, font=f_v_name)
        draw_text_outline(draw, (vx + col_w - 10, vy + 8), f"{v_pct:.1f}%", f_badge, fill=pct_color, outline=(0, 0, 0), outline_width=1, anchor="ra")
        draw.text((vx + 10, vy + 24), f"{v_op:,.1f} / {v_max:,.1f}", fill=cell_fg, font=f_v_op)
        draw.text((vx + col_w - 10, vy + 24), p_info["name"], fill=cell_fg, font=f_v_op, anchor="ra")

    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    out_buf.seek(0)
    return out_buf

def generate_levels_card(latest_snapshot: dict) -> io.BytesIO:
    """
    Renders an 840x560 dark mode profile card with gradient banner and 23-level folders grid.
    """
    width, height = 840, 560
    img = Image.new("RGB", (width, height), DARK_BG)
    _draw_card_header(img, latest_snapshot, width)
    draw = ImageDraw.Draw(img)

    levels_map = {item.get("level"): item for item in latest_snapshot.get("levels_data", [])}
    cols, rows = 3, 8
    card_margin_x = 16
    start_y = 126
    grid_w = width - (card_margin_x * 2)
    col_w = (grid_w - (10 * (cols - 1))) // cols
    row_h = 46

    f_v_name = get_font(12, bold=True)
    f_v_op = get_font(10, bold=False)
    f_badge = get_font(11, bold=True)

    cell_templates = {p_id: generate_gradient_badge(p_id, col_w, row_h, radius=6) for p_id in range(5)}

    for i, lvl in enumerate(LEVELS_ORDER):
        c, r = i % cols, i // cols
        vx = card_margin_x + c * (col_w + 10)
        vy = start_y + r * (row_h + 6)

        item = levels_map.get(lvl, {})
        pos = item.get("possession", 0)
        v_op = float(item.get("level_op", 0.0))
        v_max = float(item.get("level_max_op", 0.0))
        v_pct = float(item.get("op_percent", 0.0))
        played = item.get("played_charts", 0)
        tot = item.get("total_charts", 0)

        p_info = PLATE_COLORS.get(pos, PLATE_COLORS[0])
        img.paste(cell_templates[pos], (vx, vy))

        cell_fg = p_info["fg"] if pos > 0 else TEXT_MUTED
        pct_color = get_op_tier_color(v_pct)

        draw.text((vx + 10, vy + 7), f"Lv {lvl}", fill=cell_fg, font=f_v_name)
        draw_text_outline(draw, (vx + col_w - 10, vy + 7), f"{v_pct:.1f}%", f_badge, fill=pct_color, outline=(0, 0, 0), outline_width=1, anchor="ra")
        draw.text((vx + 10, vy + 26), f"{v_op:,.1f} / {v_max:,.1f}", fill=cell_fg, font=f_v_op)
        p_name = p_info["name"]
        prog_str = f"{p_name} ({played}/{tot})" if tot > 0 else p_name
        draw.text((vx + col_w - 10, vy + 26), prog_str, fill=cell_fg, font=f_v_op, anchor="ra")

    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    out_buf.seek(0)
    return out_buf

def generate_history_graph_image(history_snapshots: list) -> io.BytesIO:
    """
    Renders an 820x420 dark mode Overpower timeline graph PNG with straight line connections.
    """
    width = 820
    height = 420
    img = Image.new("RGB", (width, height), DARK_BG)
    draw = ImageDraw.Draw(img)

    pad_left = 75
    pad_right = 45
    pad_top = 50
    pad_bottom = 55

    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    f_title = get_font(16, bold=True)
    f_axis = get_font(10, bold=False)
    f_node = get_font(10, bold=True)

    draw.text((width // 2, 20), "Overpower Growth Timeline", fill=TEXT_WHITE, font=f_title, anchor="ma")

    points = []
    for snap in history_snapshots:
        ts = snap.get("timestamp", "")
        plays = snap.get("play_count", "")
        all_item = next((item for item in snap.get("data", []) if item.get("version") == "ALL"), None)
        if all_item:
            op = float(all_item.get("version_op", 0.0))
            max_op = float(all_item.get("version_max_op", 0.0))
            points.append({"timestamp": ts, "play_count": plays, "op": op, "max_op": max_op})

    if not points:
        draw.text((width // 2, height // 2), "No snapshot history recorded.", fill=TEXT_MUTED, font=f_title, anchor="mm")
        out_buf = io.BytesIO()
        img.save(out_buf, format="PNG")
        out_buf.seek(0)
        return out_buf

    ops = [p["op"] for p in points]
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
        draw.line([(pad_left, y_pos), (width - pad_right, y_pos)], fill=GRID_LINE, width=1)
        draw.text((pad_left - 10, y_pos), f"{y_val:,.0f}", fill=TEXT_MUTED, font=f_axis, anchor="rm")

    n = len(points)
    coords = []
    for i, p in enumerate(points):
        x = (pad_left + plot_w / 2) if n == 1 else pad_left + (i / (n - 1)) * plot_w
        y_ratio = (p["op"] - y_min) / (y_max - y_min) if (y_max > y_min) else 0.5
        y = pad_top + plot_h - (y_ratio * plot_h)
        coords.append((x, y, p))

        short_ts = p["timestamp"][5:16] if len(p["timestamp"]) >= 16 else p["timestamp"]
        label_text = f"#{p['play_count']}" if p.get("play_count") else short_ts
        draw.text((x, height - pad_bottom + 16), label_text, fill=TEXT_MUTED, font=f_axis, anchor="mm")

    # Shaded Area Polygon & Connecting Lines
    if len(coords) >= 2:
        poly = [(coords[0][0], pad_top + plot_h)] + [(cx, cy) for cx, cy, _ in coords] + [(coords[-1][0], pad_top + plot_h)]
        draw.polygon(poly, fill=(15, 41, 66))
        for j in range(len(coords) - 1):
            draw.line([(coords[j][0], coords[j][1]), (coords[j + 1][0], coords[j + 1][1])], fill=ACCENT_CYAN, width=3)

    # Point Nodes & Labels
    for x, y, p in coords:
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=ACCENT_CYAN, outline=(255, 255, 255), width=2)
        draw.text((x, y - 14), f"{p['op']:,.1f}", fill=TEXT_WHITE, font=f_node, anchor="mm")

    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    out_buf.seek(0)
    return out_buf
