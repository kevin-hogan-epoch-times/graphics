from flask import Flask, render_template, send_file
import requests
import xml.etree.ElementTree as ET
import json
from io import BytesIO
import time
import os

app = Flask(__name__)

API_KEY = "your_api_key_here"
BASE_URL = "https://api.ap.org/v2/elections"

COUNTY_LIMIT = 50  # <-- Change this to 100, 1000, or 3000
SLEEP_SECONDS = 3  # seconds between each API call

state_to_abbr = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawai?i": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/download")
def download_counties():
    with open(os.path.join("static", "counties_list.json"), "r") as f:
        counties = json.load(f)

    counties = counties[:COUNTY_LIMIT]
    results = {"2020": {}, "2024": {}}

    for i, county in enumerate(counties):
        state_name = county["State"]
        county_name = county["County"]
        abbr = state_to_abbr.get(state_name)
        if not abbr:
            continue

        for year, date in [("2020", "2020-11-03"), ("2024", "2024-11-05")]:
            url = f"{BASE_URL}/{date}?statepostal={abbr}&raceTypeId=G&raceId=0&level=ru"
            headers = {"x-api-key": API_KEY}
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200:
                    continue
                root = ET.fromstring(response.text)
                for ru in root.iter("ReportingUnit"):
                    if ru.attrib.get("Name") == county_name.replace(" County", ""):
                        result = []
                        for c in ru.findall("Candidate"):
                            result.append({
                                "name": f"{c.attrib.get('First')} {c.attrib.get('Last')}",
                                "party": c.attrib.get("Party"),
                                "votes": c.attrib.get("VoteCount")
                            })
                        results[year].setdefault(abbr, {})[county_name] = result
                        break
            except Exception as e:
                print(f"Error for {county_name}, {state_name}: {e}")

        print(f"[{i+1}/{COUNTY_LIMIT}] Processed {county_name}, {state_name}")
        time.sleep(SLEEP_SECONDS)

    buffer = BytesIO()
    buffer.write(json.dumps(results, indent=2).encode())
    buffer.seek(0)
    return send_file(buffer, mimetype="application/json", as_attachment=True,
                     download_name=f"election_results_{COUNTY_LIMIT}_counties.json")

if __name__ == "__main__":
    app.run(debug=True)
