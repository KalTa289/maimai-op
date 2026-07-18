import json
from pathlib import Path
from lib import *

all_op = 0.0
all_max_op = 0.0
folder_path = Path('userData')
versions_data = []

with open("versions.json", "r", encoding="utf-8") as f:
    versions = json.load(f)

for version in versions:
    version_op = 0.0
    version_max_op = 0.0
    op_percent = 0.0
    master_list = []
    remaster_list = []
    remaster_dict = {}

    # load files
    file_path_master = f"userData/{version}_MASTER.json"
    file_path_remaster = f"userData/{version}_RE_MASTER.json"

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
    for diff, chart_list in [("master", master_list), ("remaster", remaster_list)]:
        if not chart_list:
            continue

        combined_charts = master_list + remaster_list
        min_score = 101.0
        posession = 0 # 0 : none, 1 : silver, 2 : gold, 3 : platinum, 4 : rainbow
        played_all = True

        for chart in chart_list:
            if not chart.get("played", False):
                posession = 0
                played_all = False
                break
                
            score_str = chart.get("percent", "0%").strip("%")
            try:
                score = float(score_str)
            except ValueError:
                posession = 0
                played_all = False
                print(f"Invalid score format for chart {chart.get('title', 'Unknown')}: {score_str}. Setting posession to 0.")
                break
                
            min_score = min(min_score, score)

        if played_all and combined_charts:
            if min_score >= 100.0000 and op_percent > 99.50:
                posession = 4
            elif min_score >= 99.0000 and op_percent > 99.00:
                posession = 3
            elif min_score >= 98.0000 and op_percent > 97.50:
                posession = 2
            elif min_score >= 97.0000:
                posession = 1
        else:
            min_score = 0.0 # reset if incomplete
        
        versions_data.append({
            "version": version, 
            "min_score": min_score, 
            "posession": posession, 
            "version_op": round(version_op, 2), 
            "version_max_op": round(version_max_op, 2), 
            "op_percent": op_percent
            })

for _ in versions_data:
    print(_)

# for version in versions:
#     # load files
#     file_path_master = f"userData/{version}_MASTER.json"
#     file_path_remaster = f"userData/{version}_RE_MASTER.json"
#     try:
#         with open(file_path_master, "r", encoding="utf-8") as f:
#             master_list = json.load(f)
#     except FileNotFoundError:
#         print(f"Master data for version {version} not found. Skipping...")
#         continue
#     try:
#         with open(file_path_remaster, "r", encoding="utf-8") as f:
#             remaster_list = json.load(f)
#         remaster_dict = {chart["title"]: chart for chart in remaster_list}
#     except FileNotFoundError:
#         print(f"Remaster data for version {version} not found. Skipping...")
#         continue

#     for master_chart in master_list:
#         title = master_chart["title"]
#         target_chart = master_chart
        
#         # compare remaster
#         if title in remaster_dict:
#             remaster_chart = remaster_dict[title]
#             if float(remaster_chart["level"]) > float(master_chart["level"]):
#                 target_chart = remaster_chart
                
#         # extract values safely
#         played = target_chart.get("played", False)
#         level = target_chart["level"]
#         lamp = target_chart.get("lamp")
#         rating = target_chart.get("rating", "0")
#         percent = target_chart.get("percent", "0%")
        
#         # calculate
#         version_op += calc_op(played, level, lamp, rating, percent)
#         version_max_op += (float(level) + 3.0) * 5.0

#     all_op += version_op
#     all_max_op += version_max_op
#     op_percent = round((version_op / version_max_op) * 100, 4)

#     print(f"{version} - Version OP: {round(version_op, 2)} out of {round(version_max_op, 2)}, OP % = {op_percent}%")
#     version_op = 0.0
#     version_max_op = 0.0

# for file in folder_path.iterdir():
#     if file.is_file() and file.name != "player_data.json":
#         versionName = file.stem.split("_")[0]
#         if file.stem.split("_")[1]  == "MASTER":
#             versionDiff = "master"
#         else:
#             versionDiff = "remaster"
#         version_data = {"version": versionName, "diff": versionDiff}
#         with open(file, "r", encoding="utf-8") as f:
#             version = json.load(f)
#     else:
#         continue
#     for chart in version:
#         # unplayed fails plate
#         if not chart.get("played", False):
#             posession = 0
#             break
                
#         score_str = chart.get("percent", "0%").strip("%")
#         try:
#             score = float(score_str)
#         except ValueError:
#             posession = 0
#             print(f"Invalid score format for chart {chart.get('title', 'Unknown')}: {score_str}. Setting posession to 0.")
#         min_score = min(min_score, score)

#     if min_score >= 100.0000 and op_percent > 99.50:
#         posession = 4
#     elif min_score >= 99.0000 and op_percent > 99.00:
#         posession = 3
#     elif min_score >= 98.0000 and op_percent > 97.50:
#         posession = 2
#     elif min_score >= 97.0000:
#         posession = 1
        
#     print(f"{file.name} - Minimum Score: {min_score}, Possession Level: {posession}")
#     version_data["min_score"] = min_score
#     version_data["posession"] = posession
#     versions_data.append(version_data)
#     min_score = 101.0  # Reset min_score for the next file

print(f"Total OP: {round(all_op, 2)} out of {round(all_max_op, 2)}, OP % = {round((all_op / all_max_op) * 100, 4)}%")