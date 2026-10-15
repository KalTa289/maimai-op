import os
import re
import sys
import html
import json
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

COMBO_BONUSES = {
    "FC": 0.5,
    "FC+": 0.75,
    "AP": 1.0,
    "AP+": 1.25,
}

LEVEL_FOLDERS_ORDER = [
    "1", "2", "3", "4", "5", "6",
    "7", "7+", "8", "8+", "9", "9+",
    "10", "10+", "11", "11+", "12", "12+",
    "13", "13+", "14", "14+", "15"
]

DIFF_NAMES = ["BASIC", "ADVANCED", "EXPERT", "MASTER", "RE_MASTER"]

def normalize_title(raw_title: str) -> str:
    """Authoritative title normalization across all modules."""
    if not raw_title:
        return "\u200b"
    t = html.unescape(raw_title).strip()
    if not t:
        return "\u200b"
    t = unicodedata.normalize("NFKC", t)
    t = t.replace("’", "'").replace("‘", "'").replace("”", '"').replace("“", '"')
    t = t.replace("◇", "◆").replace("&#9670;", "◆").replace("&#9671;", "◆")
    return re.sub(r'\s+', ' ', t).strip()

def calc_op(
    played: bool,
    level_str: str | float,
    lamp: str | None = None,
    rating_str: str | float | None = None,
    percent_str: str | float = "0%"
) -> float:
    """
    Calculates Overpower (OP) for a single chart based on level, achievement score, and combo lamp.
    Piecewise continuous formula from overpower_possession.md:
    - Below S (< 97.0%): 0.0
    - S (97.0% ~ 97.9999%): level * 5.0 + ((score - 97.0) / 1.0) * 2.5 + combo_bonus
    - S+ (98.0% ~ 98.9999%): (level + 0.5) * 5.0 + ((score - 98.0) / 1.0) * 2.5 + combo_bonus
    - SS (99.0% ~ 99.4999%): (level + 1.0) * 5.0 + ((score - 99.0) / 0.5) * 2.5 + combo_bonus
    - SS+ (99.5% ~ 99.9999%): (level + 1.5) * 5.0 + ((score - 99.5) / 0.5) * 2.5 + combo_bonus
    - SSS or above (100.0% ~ 100.9999%): (level + 2.0) * 5.0 + (score - 100.0) * 3.75 + combo_bonus
    - AP+ / Theoretical Max (101.0% with AP+): (level + 3.0) * 5.0
    """
    if not played:
        return 0.0

    try:
        level = float(level_str)
    except (ValueError, TypeError):
        return 0.0

    if isinstance(percent_str, (int, float)):
        score = float(percent_str)
    else:
        try:
            score = float(str(percent_str).rstrip("%"))
        except (ValueError, TypeError):
            return 0.0

    if score < 97.0:
        return 0.0

    combo_bonus = COMBO_BONUSES.get(lamp, 0.0) if lamp else 0.0
    score = min(score, 101.0)

    if score >= 100.0:
        op = (level + 2.0) * 5.0 + (score - 100.0) * 3.75 + combo_bonus
    elif score >= 99.5:
        op = (level + 1.5) * 5.0 + ((score - 99.5) / 0.5) * 2.5 + combo_bonus
    elif score >= 99.0:
        op = (level + 1.0) * 5.0 + ((score - 99.0) / 0.5) * 2.5 + combo_bonus
    elif score >= 98.0:
        op = (level + 0.5) * 5.0 + ((score - 98.0) / 1.0) * 2.5 + combo_bonus
    else:  # 97.0 <= score < 98.0
        op = level * 5.0 + ((score - 97.0) / 1.0) * 2.5 + combo_bonus

    max_possible_op = (level + 3.0) * 5.0
    op = min(op, max_possible_op)
    return round(op, 4)

def calc_possession_plate(min_score: float, op_percent: float) -> int:
    """
    Calculates possession plate tier (0=None, 1=Silver, 2=Gold, 3=Platinum, 4=Rainbow)
    based on the lowest score achieved across required charts and the OP percentage.
    - Rainbow (4): min_score >= 99.0% (all SS) and op_percent >= 99.50%
    - Platinum (3): min_score >= 98.0% (all S+) and op_percent >= 99.00%
    - Gold (2): min_score >= 98.0% (all S+) and op_percent >= 97.50%
    - Silver (1): min_score >= 97.0% (all S)
    - None (0): default
    """
    if min_score >= 99.0 and op_percent >= 99.50:
        return 4
    if min_score >= 98.0 and op_percent >= 99.00:
        return 3
    if min_score >= 98.0 and op_percent >= 97.50:
        return 2
    if min_score >= 97.0:
        return 1
    return 0

def calc_distributions(charts: list[dict]) -> tuple[dict, dict]:
    """
    Counts rank achievements and lamps across a collection of charts.
    """
    ranks = {"S": 0, "S+": 0, "SS": 0, "SS+": 0, "SSS": 0, "SSS+": 0}
    lamps = {"FC": 0, "FC+": 0, "AP": 0, "AP+": 0}

    for c in charts:
        if not c.get("played"):
            continue
        try:
            score = float(str(c.get("percent", "0%")).rstrip("%"))
        except (ValueError, TypeError):
            score = 0.0

        if score >= 100.5:
            ranks["SSS+"] += 1
        if score >= 100.0:
            ranks["SSS"] += 1
        if score >= 99.5:
            ranks["SS+"] += 1
        if score >= 99.0:
            ranks["SS"] += 1
        if score >= 98.0:
            ranks["S+"] += 1
        if score >= 97.0:
            ranks["S"] += 1

        lamp = c.get("lamp")
        if lamp in lamps:
            lamps[lamp] += 1

    return ranks, lamps

def load_json(path: Path | str, default: Any = None) -> Any:
    if default is None:
        default = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def atomic_write_json(filepath: Path | str, data: Any, indent: int = 2) -> None:
    """Safely writes JSON data to disk via an atomic temporary file replacement."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f".tmp_{os.getpid()}_{int(time.time() * 1000)}")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    temp_path.replace(path)

def get_level_folder(level_ds: float | str) -> str:
    val = round(float(level_ds), 1)
    base = int(val)
    frac = round(val - base, 1)
    if base < 7:
        return str(base)
    if base >= 15:
        return "15"
    return f"{base}+" if frac >= 0.7 else str(base)

def level_sort_key(folder_name: str) -> float:
    try:
        clean = folder_name.replace("Lv", "").replace("LV", "").strip()
        if clean.endswith("+"):
            return float(clean[:-1]) + 0.5
        return float(clean)
    except ValueError:
        return 999.0

def calculate_for_user(user_id: str, player_data: dict | None = None) -> list:
    if not re.match(r"^[a-zA-Z0-9_\-]+$", user_id):
        raise ValueError(f"Invalid user ID format: '{user_id}'")

    user_dir = Path(f"users/{user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)
    records_dir = user_dir / "records"
    records_dir.mkdir(exist_ok=True)

    all_op = 0.0
    all_max_op = 0.0
    all_mas_remas_charts = []
    versions_data = []
    level_buckets = {k: [] for k in LEVEL_FOLDERS_ORDER}

    versions = load_json("data/versions.json", [])
    if not versions:
        print("Warning: data/versions.json not found or empty.")
        return []

    for version in versions:
        ver_charts_by_diff = {}
        has_any_charts = False
        for d in DIFF_NAMES:
            c_list = load_json(records_dir / f"{version}_{d}.json", [])
            ver_charts_by_diff[d] = c_list
            if c_list:
                has_any_charts = True

        if not has_any_charts:
            continue

        # Group charts by distinct song entity: (title, type) across all 5 difficulties
        songs = {}
        for d in DIFF_NAMES:
            for chart in ver_charts_by_diff[d]:
                key = (normalize_title(chart["title"]), chart.get("type", "Standard"))
                chart_entry = dict(chart)
                chart_entry["diff"] = d
                songs.setdefault(key, []).append(chart_entry)

        version_op = 0.0
        version_max_op = 0.0

        for song_key, song_charts in songs.items():
            best_chart_op = max((calc_op(
                c.get("played", False),
                c["level"],
                c.get("lamp"),
                c.get("rating", "0"),
                c.get("percent", "0%")
            ) for c in song_charts), default=0.0)

            song_max_level = max((float(c["level"]) for c in song_charts), default=0.0)
            song_max_op = (song_max_level + 3.0) * 5.0

            version_op += best_chart_op
            version_max_op += song_max_op

        all_op += version_op
        all_max_op += version_max_op
        op_percent = (version_op / version_max_op * 100) if version_max_op > 0 else 0.0

        # Possession plate evaluated on MASTER and RE_MASTER charts
        combined_mas_remas = ver_charts_by_diff.get("MASTER", []) + ver_charts_by_diff.get("RE_MASTER", [])
        all_mas_remas_charts.extend(combined_mas_remas)

        all_played = all(c.get("played", False) for c in combined_mas_remas) if combined_mas_remas else False
        min_score = (
            min((float(c.get("percent", "0%").rstrip("%")) for c in combined_mas_remas), default=0.0)
            if all_played
            else 0.0
        )

        possession = calc_possession_plate(min_score, op_percent)
        v_ranks, v_lamps = calc_distributions([c for sub in ver_charts_by_diff.values() for c in sub])

        versions_data.append({
            "version": version,
            "possession": possession,
            "version_op": round(version_op, 2),
            "version_max_op": round(version_max_op, 2),
            "op_percent": round(op_percent, 2),
            "min_score": round(min_score, 4) if all_played else 0.0,
            "rank_counts": v_ranks,
            "lamp_counts": v_lamps
        })

    # Overall ALL entry
    all_pct = (all_op / all_max_op * 100) if all_max_op > 0 else 0.0
    all_mas_played = all(c.get("played", False) for c in all_mas_remas_charts) if all_mas_remas_charts else False
    all_min_score = (
        min((float(c.get("percent", "0%").rstrip("%")) for c in all_mas_remas_charts), default=0.0)
        if all_mas_played
        else 0.0
    )
    all_possession = calc_possession_plate(all_min_score, all_pct)
    all_ranks = {
        r: sum(item.get("rank_counts", {}).get(r, 0) for item in versions_data)
        for r in ["S", "S+", "SS", "SS+", "SSS", "SSS+"]
    }
    all_lamps = {
        l: sum(item.get("lamp_counts", {}).get(l, 0) for item in versions_data)
        for l in ["FC", "FC+", "AP", "AP+"]
    }

    all_entry = {
        "version": "ALL",
        "possession": all_possession,
        "version_op": round(all_op, 2),
        "version_max_op": round(all_max_op, 2),
        "op_percent": round(all_pct, 2),
        "min_score": round(all_min_score, 4) if all_mas_played else 0.0,
        "rank_counts": all_ranks,
        "lamp_counts": all_lamps
    }
    versions_data.append(all_entry)

    # Level Folders
    for version in versions:
        for d_name in DIFF_NAMES:
            c_list = load_json(records_dir / f"{version}_{d_name}.json", [])
            for chart in c_list:
                lvl_str = chart.get("level")
                if lvl_str:
                    folder = get_level_folder(lvl_str)
                    chart_copy = dict(chart)
                    chart_copy["diff"] = d_name
                    chart_copy["version"] = version
                    level_buckets.setdefault(folder, []).append(chart_copy)

    levels_data = []
    for folder in LEVEL_FOLDERS_ORDER:
        charts = level_buckets.get(folder, [])
        if not charts:
            continue

        l_op = sum(calc_op(
            c.get("played", False),
            c["level"],
            c.get("lamp"),
            c.get("rating", "0"),
            c.get("percent", "0%")
        ) for c in charts)
        l_max_op = sum((float(c["level"]) + 3.0) * 5.0 for c in charts)
        pct = (l_op / l_max_op * 100) if l_max_op > 0 else 0.0

        all_p = all(c.get("played", False) for c in charts)
        min_s = min((float(c.get("percent", "0%").rstrip("%")) for c in charts), default=0.0) if all_p else 0.0
        played_cnt = sum(1 for c in charts if c.get("played"))

        pos = calc_possession_plate(min_s, pct)
        l_ranks, l_lamps = calc_distributions(charts)

        levels_data.append({
            "level": folder,
            "possession": pos,
            "level_op": round(l_op, 2),
            "level_max_op": round(l_max_op, 2),
            "op_percent": round(pct, 2),
            "total_charts": len(charts),
            "played_charts": played_cnt,
            "min_score": round(min_s, 4) if all_p else 0.0,
            "rank_counts": l_ranks,
            "lamp_counts": l_lamps
        })

    # Historical Deltas & Session Tracking
    history_file = user_dir / "history.json"
    history = load_json(history_file, [])

    prev_snapshot_map = {}
    prev_levels_map = {}
    if history:
        last_snapshot = history[-1]
        prev_snapshot_map = {item["version"]: item for item in last_snapshot.get("data", [])}
        prev_levels_map = {item["level"]: item for item in last_snapshot.get("levels_data", [])}

    for item in versions_data:
        v_name = item["version"]
        prev = prev_snapshot_map.get(v_name)
        if prev:
            item["delta_op"] = round(item["version_op"] - prev.get("version_op", item["version_op"]), 2)
            item["delta_possession"] = item["possession"] - prev.get("possession", item["possession"])
        else:
            item["delta_op"] = 0.0
            item["delta_possession"] = 0

    for item in levels_data:
        lvl_name = item["level"]
        prev = prev_levels_map.get(lvl_name)
        if prev:
            item["delta_op"] = round(item["level_op"] - prev.get("level_op", item["level_op"]), 2)
            item["delta_possession"] = item["possession"] - prev.get("possession", item["possession"])
        else:
            item["delta_op"] = 0.0
            item["delta_possession"] = 0

    meta = player_data or (history[-1] if history else {})
    username = meta.get("username", user_id)
    play_count = meta.get("play_count", "")
    version_play_count = meta.get("version_play_count", "")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prev_play_count = history[-1].get("play_count") if history else None
    if not history:
        has_changed = True
    elif play_count and prev_play_count:
        has_changed = (str(play_count) != str(prev_play_count))
    else:
        prev_all_op = next((item.get("version_op") for item in history[-1].get("data", []) if item.get("version") == "ALL"), None)
        has_changed = (round(all_op, 2) != prev_all_op)

    if has_changed:
        history.append({
            "timestamp": timestamp,
            "username": username,
            "play_count": play_count,
            "version_play_count": version_play_count,
            "data": versions_data,
            "levels_data": levels_data
        })
    elif history:
        # Preserve existing session deltas if scores/play count have not changed
        prev_data_map = {item["version"]: item for item in history[-1].get("data", [])}
        for item in versions_data:
            if item["version"] in prev_data_map:
                item["delta_op"] = prev_data_map[item["version"]].get("delta_op", 0.0)
                item["delta_possession"] = prev_data_map[item["version"]].get("delta_possession", 0)

        prev_lvl_map = {item["level"]: item for item in history[-1].get("levels_data", [])}
        for item in levels_data:
            if item["level"] in prev_lvl_map:
                item["delta_op"] = prev_lvl_map[item["level"]].get("delta_op", 0.0)
                item["delta_possession"] = prev_lvl_map[item["level"]].get("delta_possession", 0)

        history[-1].update({
            "username": username,
            "play_count": play_count,
            "version_play_count": version_play_count,
            "data": versions_data,
            "levels_data": levels_data
        })

    atomic_write_json(history_file, history)
    print(f"[{user_id}] Calculation completed ({len(versions_data)} versions, {len(levels_data)} levels) -> saved to history.json.")
    return versions_data

def main():
    if len(sys.argv) > 1:
        user_ids = [sys.argv[1]]
    else:
        users_base = Path("users")
        if users_base.exists():
            user_ids = [d.name for d in users_base.iterdir() if d.is_dir()]
        else:
            user_ids = ["kalta"]

    if not user_ids:
        user_ids = ["kalta"]

    for u_id in user_ids:
        calculate_for_user(u_id)

if __name__ == "__main__":
    main()