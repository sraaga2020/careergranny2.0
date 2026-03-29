import json
import re

INPUT_FILE = "firecrawl_output.json"
OUTPUT_FILE = "ivy_scholars_db.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

content = data.get("markdown")
if not content:
    raise ValueError("Markdown content not found in JSON")

sections = re.split(r"\n#{3,4}\s*", content)
sections = [s.strip() for s in sections if s.strip()]

database = []

for section in sections:
    heading_match = re.match(r"(?:Pros|Cons|Skip to content|Book Your Complimentary Consultation|Other Services)?\s*-?\s*(.*)", section, re.IGNORECASE)
    if not heading_match:
        continue

    name = heading_match.group(1).strip()
    if not name or name.lower() in ["pros", "cons", "skip to content", "book your complimentary consultation", "other services"]:
        continue

    # Remove heading from description
    description = re.sub(r"^.*?\n", "", section, count=1).strip()
    database.append({
        "name": name,
        "description": re.sub(r"\s+", " ", description)
    })

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(database, f, indent=4)

print(f"Extracted {len(database)} programs into {OUTPUT_FILE}")



