import pandas as pd
import json
from collections import defaultdict

# -----------------------------
# Load dataset
# -----------------------------
df = pd.read_csv("./sharegpt_travel.csv")

# -----------------------------
# Keyword rules
# -----------------------------
SEASON_RULES = {
    "Spring": ["spring", "march", "april"],
    "Summer": ["summer", "beach", "vacation", "june", "july"],
    "Autumn": ["autumn", "fall", "september", "october"],
    "Winter": ["winter", "snow", "december", "cold"]
}

PLACE_RULES = {
    "Beach": ["beach", "island", "seaside"],
    "Mountain": ["mountain", "hill", "trek"],
    "City": ["city", "urban", "downtown"],
    "Cultural": ["heritage", "temple", "museum"],
    "Other": ["safari", "countryside"]
}

ACTIVITY_RULES = {
    "Adventure": ["adventure", "trek", "hike"],
    "Leisure": ["relax", "leisure", "calm"],
    "Cultural": ["culture", "heritage"],
    "General": ["plan", "itinerary", "trip"]
}

# -----------------------------
# Inference helpers
# -----------------------------
def infer_category(text, rules, default=None):
    text = text.lower()
    for key, keywords in rules.items():
        if any(k in text for k in keywords):
            return key
    return default

# -----------------------------
# Aggregate hierarchy
# -----------------------------
hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

for text in df["text"].dropna():
    text = str(text)

    season = infer_category(text, SEASON_RULES, None)
    place = infer_category(text, PLACE_RULES, None)
    activity = infer_category(text, ACTIVITY_RULES, "General")

    if season and place:
        hierarchy[season][place][activity] += 1

# -----------------------------
# Build sunburst JSON
# -----------------------------
sunburst_json = {
    "name": "Travel Preferences",
    "children": []
}

for season, places in hierarchy.items():
    season_node = {"name": season, "children": []}

    for place, activities in places.items():
        place_node = {"name": place, "children": []}

        for activity, count in activities.items():
            place_node["children"].append({
                "name": activity,
                "value": count
            })

        season_node["children"].append(place_node)

    sunburst_json["children"].append(season_node)

# -----------------------------
# Save JSON
# -----------------------------
with open("seasonal_sunburst.json", "w") as f:
    json.dump(sunburst_json, f, indent=2)

print("✅ Seasonal sunburst JSON generated")
