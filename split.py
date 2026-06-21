import json

with open(
    "world_universities_and_domains.json",
    "r",
    encoding="utf-8"
) as f:
    data = json.load(f)

uk = []

for university in data:

    if university["country"] == "United Kingdom":

        uk.append({

            "name": university["name"],

            "domains": university["domains"]

        })

with open(
    "uk_universities.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        uk,
        f,
        ensure_ascii=False,
        indent=2
    )