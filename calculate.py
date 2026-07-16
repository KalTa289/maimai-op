import json
from pathlib import Path
from lib import *

all_op = 0.0
all_max_op = 0.0
version_op = 0.0
version_max_op = 0.0

with open("versions.json", "r", encoding="utf-8") as f:
    versions = json.load(f)

for version in versions:
    # load files
    file_path_master = f"userData/{version}_MASTER.json"
    file_path_remaster = f"userData/{version}_RE_MASTER.json"
    try:
        with open(file_path_master, "r", encoding="utf-8") as f:
            master_list = json.load(f)
    except FileNotFoundError:
        print(f"Master data for version {version} not found. Skipping...")
        continue
    try:
        with open(file_path_remaster, "r", encoding="utf-8") as f:
            remaster_list = json.load(f)
        remaster_dict = {chart["title"]: chart for chart in remaster_list}
    except FileNotFoundError:
        print(f"Remaster data for version {version} not found. Skipping...")
        continue

    for master_chart in master_list:
        title = master_chart["title"]
        target_chart = master_chart
        
        # compare remaster
        if title in remaster_dict:
            remaster_chart = remaster_dict[title]
            if float(remaster_chart["level"]) > float(master_chart["level"]):
                target_chart = remaster_chart
                
        # extract values safely
        played = target_chart.get("played", False)
        level = target_chart["level"]
        lamp = target_chart.get("lamp")
        rating = target_chart.get("rating", "0")
        percent = target_chart.get("percent", "0%")
        
        # calculate
        version_op += calc_op(played, level, lamp, rating, percent)
        version_max_op += (float(level) + 3.0) * 5.0

    all_op += version_op
    all_max_op += version_max_op
    print(f"{version} - Version OP: {round(version_op, 2)} out of {round(version_max_op, 2)}, OP % = {round((version_op / version_max_op) * 100, 4)}%")
print(f"Total OP: {round(all_op, 2)} out of {round(all_max_op, 2)}, OP % = {round((all_op / all_max_op) * 100, 4)}%")