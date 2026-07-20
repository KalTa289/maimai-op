import json
from lib import *

all_op = 0.0
all_max_op = 0.0
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

    # calculate OP
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

    # calculate possession plates
    overall_min_score = 101.0
    posession = 0
    combined_charts = master_list + remaster_list

    # skip empty lists
    if not master_list and not remaster_list:
        overall_min_score = 0.0
    else:
        for chart in combined_charts:
            # unplayed instantly fails plate. break loop.
            if not chart.get("played", False):
                overall_min_score = 0.0
                break
            try:
                score = float(chart.get("percent", "0%").strip("%"))
                # direct comparison faster than min()
                if score < overall_min_score:
                    overall_min_score = score
            except ValueError:
                overall_min_score = 0.0
                break

    if overall_min_score >= 100.0000 and op_percent > 99.50:
        posession = 4
    elif overall_min_score >= 99.0000 and op_percent > 99.00:
        posession = 3
    elif overall_min_score >= 98.0000 and op_percent > 97.50:
        posession = 2
    elif overall_min_score >= 97.0000 and op_percent > 0.0:
        posession = 1
    else:
        posession = 0
   
    versions_data.append({
        "version": version,
        "posession": posession, 
        "version_op": round(version_op, 2), 
        "version_max_op": round(version_max_op, 2), 
        "op_percent": op_percent
        })

versions_data.append({"all_op": round(all_op, 2), "all_max_op": round(all_max_op, 2), "all_op_percent": round((all_op / all_max_op) * 100, 4) if all_max_op > 0 else 0.0})
with open("data/versions_data.json", "w", encoding="utf-8") as f:
    json.dump(versions_data, f)