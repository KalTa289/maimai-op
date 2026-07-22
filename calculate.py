import json
from lib import *

all_op = 0.0
all_max_op = 0.0
all_op_percent = 0.0
all_possession = 4
versions_data = []

with open("data/versions.json", "r", encoding="utf-8") as f:
    versions = json.load(f)

for version in versions:
    version_op = 0.0
    version_max_op = 0.0
    op_percent = 0.0
    master_list = []
    remaster_list = []
    remaster_dict = {}

    # load files
    file_path_master = f"records/{version}_MASTER.json"
    file_path_remaster = f"records/{version}_RE_MASTER.json"

    try:
        with open(file_path_master, "r", encoding="utf-8") as f:
            master_list = json.load(f)
    except FileNotFoundError:
        print(f"Master data for version {version} not found. Skipping...")
    try:
        with open(file_path_remaster, "r", encoding="utf-8") as f:
            remaster_list = json.load(f)
        remaster_dict = {chart["title"]: chart for chart in remaster_list}
    except FileNotFoundError:
        print(f"Remaster data for version {version} not found. Skipping...")
    if not master_list and not remaster_list:
        continue

    for master_chart in master_list:
        title = master_chart["title"]
        target_chart = master_chart
        
        if title in remaster_dict:
            remaster_chart = remaster_dict[title]
            if float(remaster_chart["level"]) > float(master_chart["level"]):
                target_chart = remaster_chart
                
        played = target_chart.get("played", False)
        level = target_chart["level"]
        lamp = target_chart.get("lamp")
        rating = target_chart.get("rating", "0")
        percent = target_chart.get("percent", "0%")
        
        version_op += calc_op(played, level, lamp, rating, percent)
        version_max_op += (float(level) + 3.0) * 5.0

    all_op += version_op
    all_max_op += version_max_op
    op_percent = round((version_op / version_max_op) * 100, 2) if version_max_op > 0 else 0.0

    min_score = 101.0
    possession = 0
    combined_charts = master_list + remaster_list

    if not master_list and not remaster_list:
        min_score = 0.0
    else:
        for chart in combined_charts:
            if not chart.get("played", False):
                min_score = 0.0
                break
            try:
                score = float(chart.get("percent", "0%").strip("%"))
                if score < min_score:
                    min_score = score
            except ValueError:
                min_score = 0.0
                break

    if min_score >= 100.0000 and op_percent > 99.50:
        possession = 4
    elif min_score >= 99.0000 and op_percent > 99.00:
        possession = 3
    elif min_score >= 98.0000 and op_percent > 97.50:
        possession = 2
    elif min_score >= 97.0000 and op_percent > 0.0:
        possession = 1
    else:
        possession = 0
   
    versions_data.append({
        "version": version,
        "possession": possession, 
        "version_op": round(version_op, 2), 
        "version_max_op": round(version_max_op, 2), 
        "op_percent": op_percent
        })

all_op_percent = round((all_op / all_max_op) * 100, 4) if all_max_op > 0 else 0.0    
for item in versions_data:
    pos = item.get("possession", 0)
    if pos < all_possession:
        all_possession = pos

versions_data.append({
    "version": "ALL",
    "possession": all_possession,
    "version_op": round(all_op, 2),
    "version_max_op": round(all_max_op, 2),
    "op_percent": all_op_percent
    })
with open("data/versions_data.json", "w", encoding="utf-8") as f:
    json.dump(versions_data, f)