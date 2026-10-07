import os
import time
import asyncio
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from calculate import (
    load_json,
    get_level_folder,
    LEVEL_FOLDERS_ORDER,
    calculate_for_user,
    calc_op,
    calc_possession_plate
)
from sync import sync_clal, is_sega_maintenance
from draw import (
    generate_profile_card,
    generate_levels_card,
    generate_history_graph_image,
    PLATE_NAMES,
    PLATE_EMOJIS)

# ==========================================
# 1. Configuration & Constants
# ==========================================

if Path(".env").exists():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=INTENTS)

PLATE_GOALS = [
    {"id": 1, "name": "Silver", "emoji": "🥈", "min_score": 97.0, "min_op": 0.0, "rank": "S"},
    {"id": 2, "name": "Gold", "emoji": "🥇", "min_score": 98.0, "min_op": 93.0, "rank": "SS"},
    {"id": 3, "name": "Platinum", "emoji": "👑", "min_score": 99.0, "min_op": 95.0, "rank": "SSS"},
    {"id": 4, "name": "Rainbow", "emoji": "🌈", "min_score": 100.0, "min_op": 97.0, "rank": "SSS+"},
]

PLATE_CHOICES = [
    app_commands.Choice(name="Next Goal (Auto)", value="auto"),
    app_commands.Choice(name="🥈 Silver (All ≥97% S)", value="silver"),
    app_commands.Choice(name="🥇 Gold (All ≥98% SS & OP ≥93%)", value="gold"),
    app_commands.Choice(name="👑 Platinum (All ≥99% SSS & OP ≥95%)", value="platinum"),
    app_commands.Choice(name="🌈 Rainbow (All ≥100% SSS+ & OP ≥97%)", value="rainbow"),
]

DIFF_SHORT_TAGS = {
    "BASIC": "BAS",
    "ADVANCED": "ADV",
    "EXPERT": "EXP",
    "MASTER": "MAS",
    "RE_MASTER": "Re:M",
}

# ==========================================
# 2. Helper Functions
# ==========================================

def get_discord_user_id(user: discord.User | discord.Member) -> str:
    return f"discord_{user.id}"

def get_user_history(user_id: str) -> list:
    return load_json(Path(f"users/{user_id}/history.json"), [])

def latest_name(history: list, default: str) -> str:
    return history[-1].get("username", default) if history else default

def get_chart_percent(chart: dict) -> float:
    p = chart.get("percent", "0%")
    return float(p.rstrip("%")) if "%" in p else 0.0

def make_sync_embed(p_data: dict, history: list) -> discord.Embed:
    latest = history[-1] if history else {}
    all_row = next((item for item in latest.get("data", []) if item.get("version") == "ALL"), None)

    embed = discord.Embed(
        title=f"✅ Sync Successful for {p_data['username']}!",
        color=0x38bdf8
    )
    embed.add_field(name="🎮 Total Plays", value=f"{int(p_data.get('play_count', 0)):,}", inline=True)
    embed.add_field(name="🕹️ This Version", value=f"{int(p_data.get('version_play_count', 0)):,}", inline=True)
    embed.add_field(name="⭐ Rating", value=str(p_data['rating']), inline=True)

    if all_row:
        op = float(all_row.get("version_op", 0.0))
        max_op = float(all_row.get("version_max_op", 0.0))
        pct = (op / max_op * 100) if max_op > 0 else 0.0
        d_op = float(all_row.get("delta_op", 0.0))
        d_str = f" ({'+' if d_op > 0 else ''}{d_op:,.2f})" if abs(d_op) > 0.001 else ""
        embed.add_field(name="⚡ Overpower", value=f"**{op:,.2f}** / {max_op:,.2f} ({pct:.2f}%){d_str}", inline=False)

    embed.set_footer(text="Use /versions or /levels to view your profile cards, or /graph for timeline!")
    return embed

async def send_versions_profile(interaction: discord.Interaction, user: Optional[discord.User] = None):
    target = user or interaction.user
    user_id = get_discord_user_id(target)
    history = get_user_history(user_id)

    if not history:
        msg = f"No records found for {target.mention}."
        if target.id == interaction.user.id:
            msg += "\nUse `/sync` to link and fetch your scores from SEGA maimai DX NET!"
        await interaction.followup.send(msg)
        return

    latest = history[-1]
    all_row = next((item for item in latest.get("data", []) if item.get("version") == "ALL"), None)

    pos = all_row.get("possession", 0) if all_row else 0
    plate_emoji = PLATE_EMOJIS.get(pos, "⬜")

    card_buf = await asyncio.to_thread(generate_profile_card, latest)
    file = discord.File(card_buf, filename="profile_card.png")

    tot_p = str(latest.get("play_count", "—"))
    ver_p = str(latest.get("version_play_count", ""))
    if tot_p.isdigit():
        p_footer = f"{int(tot_p):,} total"
        if ver_p.isdigit() and int(ver_p) != int(tot_p):
            p_footer += f" ({int(ver_p):,} this ver)"
    else:
        p_footer = tot_p

    embed = discord.Embed(
        title=f"{plate_emoji} Version Overpower for {latest.get('username', target.display_name)}",
        color=0x38bdf8
    )
    embed.set_image(url="attachment://profile_card.png")
    embed.set_footer(text=f"Last Synced: {latest.get('timestamp', '—')} • Plays: {p_footer}")

    await interaction.followup.send(embed=embed, file=file)

async def send_levels_profile(interaction: discord.Interaction, user: Optional[discord.User] = None):
    target = user or interaction.user
    user_id = get_discord_user_id(target)
    history = get_user_history(user_id)

    if not history or not history[-1].get("levels_data"):
        # Check if user has record files to calculate from
        user_dir = Path(f"users/{user_id}/records")
        if user_dir.exists() and list(user_dir.glob("*.json")):
            await asyncio.to_thread(calculate_for_user, user_id)
            history = get_user_history(user_id)

    if not history or not history[-1].get("levels_data"):
        msg = f"No level folder records found for {target.mention}."
        if target.id == interaction.user.id:
            msg += "\nUse `/sync` to link and fetch your scores from SEGA maimai DX NET!"
        await interaction.followup.send(msg)
        return

    # Auto-repair stale levels_data from previous single-version bug
    tot_charts = sum(l.get("total_charts", 0) for l in history[-1].get("levels_data", []))
    if tot_charts < 1000:
        await asyncio.to_thread(calculate_for_user, user_id)
        history = get_user_history(user_id)

    latest = history[-1]
    all_row = next((item for item in latest.get("data", []) if item.get("version") == "ALL"), None)
    pos = all_row.get("possession", 0) if all_row else 0
    plate_emoji = PLATE_EMOJIS.get(pos, "⬜")

    card_buf = await asyncio.to_thread(generate_levels_card, latest)
    file = discord.File(card_buf, filename="levels_card.png")

    tot_p = str(latest.get("play_count", "—"))
    ver_p = str(latest.get("version_play_count", ""))
    if tot_p.isdigit():
        p_footer = f"{int(tot_p):,} total"
        if ver_p.isdigit() and int(ver_p) != int(tot_p):
            p_footer += f" ({int(ver_p):,} this ver)"
    else:
        p_footer = tot_p

    embed = discord.Embed(
        title=f"🎯 {plate_emoji} Level Overpower for {latest.get('username', target.display_name)}",
        color=0x38bdf8
    )
    embed.set_image(url="attachment://levels_card.png")
    embed.set_footer(text=f"Last Synced: {latest.get('timestamp', '—')} • Plays: {p_footer}")

    await interaction.followup.send(embed=embed, file=file)

async def version_autocomplete(interaction: discord.Interaction, current: str):
    versions = load_json("data/versions.json", [])
    return [
        app_commands.Choice(name=v, value=v)
        for v in versions if current.lower() in v.lower()
    ][:25]

async def level_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=f"Lv {f}", value=f)
        for f in LEVEL_FOLDERS_ORDER if current.lower() in f.lower() or current.lower() in f"lv {f}".lower()
    ][:25]

# ==========================================
# 3. UI Modals & Views
# ==========================================

class TokenExpiredView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="🔑 Enter New CLAL Token", style=discord.ButtonStyle.primary)
    async def enter_token_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ClalSyncModal())

def make_progress_embed(steps: dict, username: str = "Player", status_note: str = "") -> discord.Embed:
    diff_labels = {
        "BASIC": ("🟢", "Basic"),
        "ADVANCED": ("🟡", "Advanced"),
        "EXPERT": ("🔴", "Expert"),
        "MASTER": ("🟣", "Master"),
        "RE_MASTER": ("⚪", "Re:Master")
    }
    lines = []
    for diff, (emoji, name) in diff_labels.items():
        state = steps.get(diff, "waiting")
        if state == "fetching":
            lines.append(f"⏳ Fetching **{emoji} {name}**...")
        elif state == "complete":
            count = steps.get(f"{diff}_count", 0)
            lines.append(f"✅ **{emoji} {name}** — Complete! ({count} cards)")
        elif state == "error":
            lines.append(f"❌ **{emoji} {name}** — Failed")
        else:
            lines.append(f"▫️ **{emoji} {name}** — Waiting...")

    if status_note:
        lines.append(f"\n{status_note}")

    embed = discord.Embed(
        title=f"🔄 Syncing maimai DX NET Scores for {username}",
        description="\n".join(lines),
        color=0x38bdf8
    )
    return embed

async def run_sync_with_progress(interaction: discord.Interaction, user_id: str, raw_token: Optional[str] = None):
    steps = {}
    player_info = {"username": "Player"}
    status_note = ["🔐 Authenticating with SEGA Aime Gateway..."]
    loop = asyncio.get_running_loop()

    initial_embed = make_progress_embed(steps, player_info["username"], "\n".join(status_note))
    await interaction.followup.send(embed=initial_embed, ephemeral=True)

    last_edit_time = 0.0

    async def update_msg(force: bool = False):
        nonlocal last_edit_time
        now = time.time()
        if not force and (now - last_edit_time < 1.2):
            return
        last_edit_time = now
        try:
            embed = make_progress_embed(steps, player_info["username"], "\n".join(status_note))
            await interaction.edit_original_response(embed=embed)
        except Exception:
            pass

    def on_progress(event, diff_name, count):
        if event == "auth":
            player_info["username"] = diff_name.get("username", "Player")
            status_note.clear()
            status_note.append(f"👤 Logged in as **{player_info['username']}** (Rating: {diff_name.get('rating', 0)})")
            asyncio.run_coroutine_threadsafe(update_msg(force=True), loop)
        elif event == "fetching":
            steps[diff_name] = "fetching"
            asyncio.run_coroutine_threadsafe(update_msg(), loop)
        elif event == "complete":
            steps[diff_name] = "complete"
            steps[f"{diff_name}_count"] = count
            asyncio.run_coroutine_threadsafe(update_msg(), loop)
        elif event == "saving":
            status_note.append("⚡ Calculating Overpower & Version Plate Ratings...")
            asyncio.run_coroutine_threadsafe(update_msg(force=True), loop)

    try:
        res = await asyncio.to_thread(sync_clal, user_id, raw_token, on_progress)
        final_embed = make_sync_embed(res["player_data"], get_user_history(user_id))
        await interaction.edit_original_response(embed=final_embed)
    except Exception as e:
        err_embed = discord.Embed(
            title="❌ Sync Failed with SEGA DX NET",
            description=f"`{e}`\n\n*If your CLAL token has expired, click below to enter a new one:*",
            color=0xef4444
        )
        view = TokenExpiredView()
        await interaction.edit_original_response(embed=err_embed, view=view)

class ClalSyncModal(discord.ui.Modal, title="maimai DX NET Sync"):
    token_input = discord.ui.TextInput(
        label="CLAL Token",
        placeholder="Paste your 64-character CLAL token.",
        required=True,
        min_length=64,
        max_length=64
    )

    async def on_submit(self, interaction: discord.Interaction):
        if is_sega_maintenance():
            embed = discord.Embed(
                title="⚠️ SEGA Server Maintenance",
                description=(
                    "SEGA maimai DX NET undergoes daily server maintenance between **04:00 and 07:00 JST**.\n"
                    "Sync is currently unavailable. Please try again after 07:00 JST!"
                ),
                color=0xf59e0b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        user_id = get_discord_user_id(interaction.user)
        raw_token = self.token_input.value.strip()
        await run_sync_with_progress(interaction, user_id, raw_token)

# ==========================================
# 4. Slash Commands
# ==========================================

@bot.tree.command(name="login", description="Enter or update your maimai DX NET CLAL token privately.")
async def login_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(ClalSyncModal())

@bot.tree.command(name="sync", description="Synchronize your latest maimai DX scores from SEGA using your CLAL token.")
async def sync_cmd(interaction: discord.Interaction):
    if is_sega_maintenance():
        embed = discord.Embed(
            title="⚠️ SEGA Server Maintenance",
            description=(
                "SEGA maimai DX NET undergoes daily server maintenance between **04:00 and 07:00 JST**.\n"
                "Sync is currently unavailable. Please try again after 07:00 JST!"
            ),
            color=0xf59e0b
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = get_discord_user_id(interaction.user)
    token_file = Path(f"users/{user_id}/auth_token.txt")

    if not token_file.exists():
        await interaction.response.send_modal(ClalSyncModal())
        return

    await interaction.response.defer(ephemeral=True)
    await run_sync_with_progress(interaction, user_id, None)

@bot.tree.command(name="versions", description="View your current Overpower, possession plates, and 27-version profile card.")
@app_commands.describe(user="The user to look up (defaults to yourself)")
async def versions_cmd(interaction: discord.Interaction, user: Optional[discord.User] = None):
    await interaction.response.defer(ephemeral=False)
    await send_versions_profile(interaction, user)

@bot.tree.command(name="levels", description="View your current Overpower, level folder plates (1~15), and visual level card.")
@app_commands.describe(user="The user to look up (defaults to yourself)")
async def levels_cmd(interaction: discord.Interaction, user: Optional[discord.User] = None):
    await interaction.response.defer(ephemeral=False)
    await send_levels_profile(interaction, user)

@bot.tree.command(name="version", description="View song completion, plate checklist, and missing charts for a specific version.")
@app_commands.describe(
    version="The version to inspect (e.g. maimai PLUS, DX, CiRCLE)",
    target="Specific plate tier to target (defaults to your next plate goal)",
    user="The user to look up (defaults to yourself)"
)
@app_commands.choices(target=PLATE_CHOICES)
@app_commands.autocomplete(version=version_autocomplete)
async def version_cmd(
    interaction: discord.Interaction,
    version: str,
    target: Optional[app_commands.Choice[str]] = None,
    user: Optional[discord.User] = None
):
    await interaction.response.defer(ephemeral=False)
    tgt_user = user or interaction.user
    user_id = get_discord_user_id(tgt_user)
    user_dir = Path(f"users/{user_id}/records")

    master_path = user_dir / f"{version}_MASTER.json"
    remaster_path = user_dir / f"{version}_RE_MASTER.json"

    if not master_path.exists() and not remaster_path.exists():
        await interaction.followup.send(
            f"❌ No records found for version **{version}** on {tgt_user.mention}'s profile. Did you `/sync`?"
        )
        return

    master_charts = load_json(master_path, [])
    remaster_charts = load_json(remaster_path, [])

    for c in master_charts:
        c["diff"] = "MAS"
    for c in remaster_charts:
        c["diff"] = "Re:MAS"

    all_charts = master_charts + remaster_charts
    total_n = len(all_charts)
    if not all_charts:
        await interaction.followup.send(f"❌ No chart data found for **{version}**.")
        return

    played = [c for c in all_charts if c.get("played")]
    history = get_user_history(user_id)
    v_row = None
    if history:
        v_row = next((item for item in history[-1].get("data", []) if item.get("version") == version), None)

    pos = v_row.get("possession", 0) if v_row else 0
    plate_name = PLATE_NAMES.get(pos, "None")
    plate_emoji = PLATE_EMOJIS.get(pos, "⬜")
    v_op = float(v_row.get("version_op", 0.0)) if v_row else 0.0
    v_max = float(v_row.get("version_max_op", 0.0)) if v_row else 0.0
    v_pct = (v_op / v_max * 100) if v_max > 0 else 0.0

    target_key = target.value if target else "auto"
    if target_key == "auto":
        next_id = min(4, max(1, pos + 1))
        target_tier = next((t for t in PLATE_GOALS if t["id"] == next_id), PLATE_GOALS[0])
    else:
        target_tier = next((t for t in PLATE_GOALS if t["name"].lower() == target_key), PLATE_GOALS[0])

    op_req = f" & OP ≥{target_tier['min_op']:.0f}%" if target_tier['min_op'] > 0 else ""
    embed = discord.Embed(
        title=f"📀 {version} — Plate Analysis for {tgt_user.display_name}",
        description=(
            f"Current: **{plate_emoji} {plate_name}** | Overpower: **{v_op:,.2f} / {v_max:,.2f} ({v_pct:.2f}%)**\n"
            f"Target Goal: **{target_tier['emoji']} {target_tier['name']}** (Requires all charts ≥{target_tier['min_score']}% {target_tier['rank']}{op_req})"
        ),
        color=0x38bdf8
    )

    checklist_lines = []
    for t in PLATE_GOALS:
        count = sum(1 for c in played if get_chart_percent(c) >= t["min_score"])
        op_met = v_pct >= t["min_op"]
        achieved = (count == total_n and op_met)
        status = "✅ Achieved" if achieved else f"**{count}/{total_n}**"
        op_info = f" [OP: {v_pct:.1f}% / {t['min_op']:.0f}% {'✓' if op_met else '✗'}]" if t['min_op'] > 0 else ""
        checklist_lines.append(f"{t['emoji']} **{t['name']}**: {status}{op_info}")

    embed.add_field(
        name="📋 Plate Milestone Checklist",
        value="\n".join(checklist_lines),
        inline=False
    )

    missing = [c for c in all_charts if not c.get("played") or get_chart_percent(c) < target_tier["min_score"]]
    missing.sort(key=lambda c: get_chart_percent(c))

    if missing:
        lines = []
        for c in missing[:12]:
            score_str = f"`{c.get('percent', '0%')}`" if c.get("played") else "*Unplayed*"
            lines.append(f"• `[{c['diff']} {c['type']}]` **{c['title']}** (Lv {c['level']}) — {score_str}")
        if len(missing) > 12:
            lines.append(f"*...and {len(missing) - 12} more*")

        embed.add_field(
            name=f"🎯 Charts to Clear for {target_tier['emoji']} {target_tier['name']} ({len(missing)} remaining)",
            value="\n".join(lines),
            inline=False
        )
    else:
        embed.add_field(
            name=f"🎉 {target_tier['emoji']} {target_tier['name']} Goal Met!",
            value=f"All **{total_n}** charts in **{version}** have reached at least **{target_tier['min_score']}% ({target_tier['rank']})**!",
            inline=False
        )

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="level", description="View song completion, plate checklist, and missing charts for a level folder (e.g. 14, 14+, 15).")
@app_commands.describe(
    level="The level folder to inspect (e.g. 14, 14+, 13, 13+, 12, 15)",
    target="Specific plate tier to target (defaults to your next plate goal)",
    user="The user to look up (defaults to yourself)"
)
@app_commands.choices(target=PLATE_CHOICES)
@app_commands.autocomplete(level=level_autocomplete)
async def level_cmd(
    interaction: discord.Interaction,
    level: str,
    target: Optional[app_commands.Choice[str]] = None,
    user: Optional[discord.User] = None
):
    await interaction.response.defer(ephemeral=False)
    tgt_user = user or interaction.user
    user_id = get_discord_user_id(tgt_user)
    user_dir = Path(f"users/{user_id}/records")
    clean_lvl = level.replace("Lv", "").replace("LV", "").strip()

    def load_level_charts():
        versions = load_json("data/versions.json", [])
        diff_names = ["BASIC", "ADVANCED", "EXPERT", "MASTER", "RE_MASTER"]
        charts = []
        for v in versions:
            for d in diff_names:
                c_list = load_json(user_dir / f"{v}_{d}.json", [])
                for c in c_list:
                    lvl_str = c.get("level")
                    if lvl_str and get_level_folder(lvl_str) == clean_lvl:
                        chart_copy = dict(c)
                        chart_copy["diff"] = DIFF_SHORT_TAGS.get(d, d)
                        chart_copy["version"] = v
                        charts.append(chart_copy)
        return charts

    level_charts = await asyncio.to_thread(load_level_charts)

    if not level_charts:
        await interaction.followup.send(
            f"❌ No charts found for level folder **Lv {clean_lvl}** on {tgt_user.mention}'s profile."
        )
        return

    total_n = len(level_charts)
    played = [c for c in level_charts if c.get("played")]

    # Compute accurate live Overpower directly from level_charts
    l_op = sum(calc_op(c.get("played", False), c["level"], c.get("lamp"), c.get("rating", "0"), c.get("percent", "0%")) for c in level_charts)
    l_max = sum((float(c["level"]) + 3.0) * 5.0 for c in level_charts)
    l_pct = (l_op / l_max * 100) if l_max > 0 else 0.0

    all_p = all(c.get("played", False) for c in level_charts)
    min_s = min((get_chart_percent(c) for c in level_charts), default=0.0) if all_p else 0.0
    pos = calc_possession_plate(min_s, l_pct)
    plate_name = PLATE_NAMES.get(pos, "None")
    plate_emoji = PLATE_EMOJIS.get(pos, "⬜")

    target_key = target.value if target else "auto"
    if target_key == "auto":
        next_id = min(4, max(1, pos + 1))
        target_tier = next((t for t in PLATE_GOALS if t["id"] == next_id), PLATE_GOALS[0])
    else:
        target_tier = next((t for t in PLATE_GOALS if t["name"].lower() == target_key), PLATE_GOALS[0])

    op_req = f" & OP ≥{target_tier['min_op']:.0f}%" if target_tier['min_op'] > 0 else ""
    embed = discord.Embed(
        title=f"🎯 Lv {clean_lvl} — Level Plate Analysis for {tgt_user.display_name}",
        description=(
            f"Current: **{plate_emoji} {plate_name}** | Overpower: **{l_op:,.2f} / {l_max:,.2f} ({l_pct:.2f}%)**\n"
            f"Target Goal: **{target_tier['emoji']} {target_tier['name']}** (Requires all charts ≥{target_tier['min_score']}% {target_tier['rank']}{op_req})"
        ),
        color=0x38bdf8
    )

    checklist_lines = []
    for t in PLATE_GOALS:
        count = sum(1 for c in played if get_chart_percent(c) >= t["min_score"])
        op_met = l_pct >= t["min_op"]
        achieved = (count == total_n and op_met)
        status = "✅ Achieved" if achieved else f"**{count}/{total_n}**"
        op_info = f" [OP: {l_pct:.1f}% / {t['min_op']:.0f}% {'✓' if op_met else '✗'}]" if t['min_op'] > 0 else ""
        checklist_lines.append(f"{t['emoji']} **{t['name']}**: {status}{op_info}")

    embed.add_field(
        name="📋 Plate Milestone Checklist",
        value="\n".join(checklist_lines),
        inline=False
    )

    missing = [c for c in level_charts if not c.get("played") or get_chart_percent(c) < target_tier["min_score"]]
    missing.sort(key=lambda c: get_chart_percent(c))

    if missing:
        lines = []
        for c in missing[:12]:
            score_str = f"`{c.get('percent', '0%')}`" if c.get("played") else "*Unplayed*"
            diff_tag = c.get('diff', 'MAS')
            lines.append(f"• `[{diff_tag} {c['type']}]` **{c['title']}** (Lv {c['level']}) — {score_str}")
        if len(missing) > 12:
            lines.append(f"*...and {len(missing) - 12} more*")

        embed.add_field(
            name=f"🎯 Charts to Clear for {target_tier['emoji']} {target_tier['name']} ({len(missing)} remaining)",
            value="\n".join(lines),
            inline=False
        )
    else:
        embed.add_field(
            name=f"🎉 {target_tier['emoji']} {target_tier['name']} Goal Met!",
            value=f"All **{total_n}** charts in **Lv {clean_lvl}** have reached at least **{target_tier['min_score']}% ({target_tier['rank']})**!",
            inline=False
        )

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="graph", description="Plot your Overpower progression timeline graph.")
@app_commands.describe(user="The user to look up (defaults to yourself)")
async def graph_cmd(interaction: discord.Interaction, user: Optional[discord.User] = None):
    await interaction.response.defer(ephemeral=False)
    target = user or interaction.user
    user_id = get_discord_user_id(target)
    history = get_user_history(user_id)

    if not history:
        msg = f"No snapshot history recorded for {target.mention}. Use `/sync` to start logging your growth!"
        await interaction.followup.send(msg)
        return

    graph_buf = await asyncio.to_thread(generate_history_graph_image, history)
    file = discord.File(graph_buf, filename="timeline_graph.png")

    desc = f"Logged across **{len(history)}** snapshot{'s' if len(history) != 1 else ''}."
    latest = history[-1]
    all_row = next((item for item in latest.get("data", []) if item.get("version") == "ALL"), None)
    if all_row:
        op = float(all_row.get("version_op", 0.0))
        max_op = float(all_row.get("version_max_op", 0.0))
        pct = (op / max_op * 100) if max_op > 0 else 0.0
        desc += f"\nCurrent: **{pct:.2f}%** ({op:,.1f} / {max_op:,.1f} OP)"

    embed = discord.Embed(
        title=f"📈 {latest_name(history, target.display_name)}'s Overpower % Growth",
        description=desc,
        color=0x38bdf8
    )
    embed.set_image(url="attachment://timeline_graph.png")
    await interaction.followup.send(embed=embed, file=file)

@bot.tree.command(name="help", description="How to use the maimai-op bot and get your CLAL token.")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(
        title="📖 maimai-op Discord Bot Guide",
        description="Track your maimai DX Overpower, possession plates, and progress directly in Discord!",
        color=0x38bdf8
    )
    embed.add_field(
        name="⚡ Available Commands",
        value=(
            "• `/sync` - Synchronize your latest scores from SEGA DX NET using your CLAL token.\n"
            "• `/versions` - View your Overpower profile card and 27-version plate breakdown.\n"
            "• `/levels` - View your Overpower profile card across all 23 level folders (1~15).\n"
            "• `/level <folder>` - View detailed completion status and unplayed charts for a level folder (e.g. `14`, `14+`, `13`).\n"
            "• `/version <name>` - View detailed completion status and unplayed charts for a version.\n"
            "• `/graph` - View your Overpower timeline growth chart."
        ),
        inline=False
    )
    embed.add_field(
        name="🔑 How to obtain your CLAL value",
        value="Follow the step-by-step guide here:\n🔗 [How to obtain CLAL value](https://github.com/KalTa289/maimai-op/wiki/How-to-obtain-CLAL-value)",
        inline=False
    )
    await interaction.followup.send(embed=embed)

# ==========================================
# 6. Bot Lifecycle & Main Execution
# ==========================================

import song_manager

@bot.event
async def on_ready():
    if bot.user:
        print(f"Logged in as {bot.user.name} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands with Discord.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

    # Automatically fetch songs & verify chart constants on bot launch in the background
    asyncio.create_task(asyncio.to_thread(song_manager.update_song_database))

def main():
    if not TOKEN:
        print("DISCORD_BOT_TOKEN is not set.")
        print("Please create a .env file with: DISCORD_BOT_TOKEN=your_bot_token_here")
        return
    bot.run(TOKEN)

if __name__ == "__main__":
    main()

