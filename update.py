import json
from gex_calc import calculate_gex

data = calculate_gex()

with open("levels.json", "w") as f:
    json.dump(data, f, indent=2)
