import json
import sys
from datetime import datetime
from pathlib import Path

COMBO_BONUSES = {"FC": 0.5, "FC+": 0.75, "AP": 1.0, "AP+": 1.25}

def calc_op(played, level_str, lamp, rating_str, percent_str):
    if not played:
        return 0.0
        
    level = float(level_str)
    rating = float(rating_str) / 20.0
    score = float(percent_str.rstrip("%"))
    combo_bonus = COMBO_BONUSES.get(lamp, 0.0)
            
    if 97.0 <= score <= 100.0:
        return rating * 5.0 + combo_bonus
    if score > 100.0:
        score_bonus = (score - 100.0) * 3.75
        return (level + 2.0) * 5.0 + combo_bonus + score_bonus
    return 0.0

def load_json(path, default=None):
    if default is None:
        default = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def calculate_for_user(user_id: str = "kalta", player_data: dict = None):
    user_dir = Path(f"users/{user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)
    records_dir = user_dir / "records"
    records_dir.mkdir(exist_ok=True)

    versions = load_json("data/versions.json", [])
    if not versions:
        print("Warning: data/versions.json not found or empty.")
        return []

    all_op = 0.0
    all_max_op = 0.0
    versions_data = []

    for version in versions:
        version_op = 0.0
        version_max_op = 0.0

        master_path = records_dir / f"{version}_MASTER.json"
        remaster_path = records_dir / f"{version}_RE_MASTER.json"

        master_list = load_json(master_path, [])
        remaster_list = load_json(remaster_path, [])

        if not master_list and not remaster_list:
            continue

        remaster_dict = {chart["title"]: chart for chart in remaster_list}

        for master_chart in master_list:
            title = master_chart["title"]
            remaster_chart = remaster_dict.get(title)
            target_chart = (
                remaster_chart
                if remaster_chart and float(remaster_chart["level"]) > float(master_chart["level"])
                else master_chart
            )
                    
            played = target_chart.get("played", False)
            level = target_chart["level"]
            lamp = target_chart.get("lamp")
            rating = target_chart.get("rating", "0")
            percent = target_chart.get("percent", "0%")
            
            version_op += calc_op(played, level, lamp, rating, percent)
            version_max_op += (float(level) + 3.0) * 5.0

        all_op += version_op
        all_max_op += version_max_op
        op_percent = (version_op / version_max_op * 100) if version_max_op > 0 else 0.0

        combined_charts = master_list + remaster_list
        all_played = all(chart.get("played", False) for chart in combined_charts)
        min_score = (
            min((float(c.get("percent", "0%").rstrip("%")) for c in combined_charts), default=0.0)
            if all_played
            else 0.0
        )

        if min_score >= 100.0 and op_percent >= 97.0:
            possession = 4
        elif min_score >= 99.0 and op_percent >= 95.0:
            possession = 3
        elif min_score >= 98.0 and op_percent >= 93.0:
            possession = 2
        elif min_score >= 97.0:
            possession = 1
        else:
            possession = 0
       
        versions_data.append({
            "version": version,
            "possession": possession, 
            "version_op": round(version_op, 2), 
            "version_max_op": round(version_max_op, 2)
        })

    all_possession = min((item.get("possession", 0) for item in versions_data), default=4)

    all_entry = {
        "version": "ALL",
        "possession": all_possession,
        "version_op": round(all_op, 2),
        "version_max_op": round(all_max_op, 2)
    }
    versions_data.append(all_entry)

    # Historical snapshots in history.json
    history_file = user_dir / "history.json"
    history = load_json(history_file, [])

    prev_snapshot_map = {}
    if history:
        last_snapshot = history[-1]
        prev_snapshot_map = {item["version"]: item for item in last_snapshot.get("data", [])}

    # Calculate deltas for each version
    for item in versions_data:
        v_name = item["version"]
        prev = prev_snapshot_map.get(v_name)
        if prev:
            item["delta_op"] = round(item["version_op"] - prev.get("version_op", item["version_op"]), 2)
            item["delta_possession"] = item["possession"] - prev.get("possession", item["possession"])
        else:
            item["delta_op"] = 0.0
            item["delta_possession"] = 0

    # Determine username and play_count
    username = user_id
    play_count = ""
    if player_data:
        username = player_data.get("username", user_id)
        play_count = player_data.get("play_count", "")
    elif history:
        username = history[-1].get("username", user_id)
        play_count = history[-1].get("play_count", "")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if data has changed compared to last snapshot
    has_changed = True
    if history:
        last_data = history[-1].get("data", [])
        last_comparison = [
            (d["version"], d["version_op"], d["possession"]) for d in last_data
        ]
        curr_comparison = [
            (d["version"], d["version_op"], d["possession"]) for d in versions_data
        ]
        has_changed = (last_comparison != curr_comparison)

    if has_changed or not history:
        history.append({
            "timestamp": timestamp,
            "username": username,
            "play_count": play_count,
            "data": versions_data
        })
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    else:
        if player_data and (history[-1].get("play_count") != play_count or history[-1].get("username") != username):
            history[-1]["username"] = username
            history[-1]["play_count"] = play_count
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"[{user_id}] Calculation completed ({len(versions_data)} entries) -> saved to history.json.")
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