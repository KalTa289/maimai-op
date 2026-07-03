import json
from lib import *

total_op = 0.0
total_max_op = 0.0

with open("master.json", "r", encoding="utf-8") as f:
    master_data = json.load(f)
master_dict = {item["title"]: item for item in master_data}

with open("remaster.json", "r", encoding="utf-8") as f:
    remaster_data = json.load(f)
remaster_dict = {item["title"]: item for item in remaster_data}

for chart in determine_diff(master_data, remaster_dict):
    max_op = calc_max_op(chart["title"], chart["difficulty"], master_dict, remaster_dict)
    op = calc_op(chart["title"], chart["difficulty"], master_dict, remaster_dict)
    total_max_op += max_op
    total_op += op

print(f"Total OP: {round(total_op, 2)}, Total Max OP: {round(total_max_op, 2)}, OP % = {round((total_op / total_max_op) * 100, 4)}%")