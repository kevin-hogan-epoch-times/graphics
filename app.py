from flask import Flask, render_template, request, jsonify, send_file
import requests
import xml.etree.ElementTree as ET
import json
from io import BytesIO
from collections import defaultdict
import os

app = Flask(__name__)

API_KEY = "4uwfiazjez9koo7aju9ig4zxhr"
BASE_URL = "https://api.ap.org/v2/elections"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/results")
def results():
    state = request.args.get("state")
    county = request.args.get("county")
    url = f"{BASE_URL}/2020-11-03?statepostal={state}&raceTypeId=G&raceId=0&level=ru"
    headers = {"x-api-key": API_KEY}

    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return jsonify({"error": "API request failed", "status": res.status_code}), 500

    root = ET.fromstring(res.text)
    for ru in root.iter("ReportingUnit"):
        if ru.attrib.get("Name") == county:
            data = []
            for c in ru.findall("Candidate"):
                data.append({
                    "name": f"{c.attrib.get('First')} {c.attrib.get('Last')}",
                    "party": c.attrib.get("Party"),
                    "votes": c.attrib.get("VoteCount")
                })
            return jsonify({"county": county, "state": state, "results": data})

    return jsonify({"error": "County not found"})

@app.route("/all-results")
def all_results():
    try:
        with open(os.path.join("static", "counties_list.json"), "r") as f:
            counties = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Error loading counties_list.json: {str(e)}"}), 500

    headers = {"x-api-key": API_KEY}
    election_data = defaultdict(dict)

    for year, date in [("2020", "2020-11-03"), ("2024", "2024-11-05")]:
        for entry in counties[:5]:
            state_name = entry["State"]
            county_name = entry["County"]
            state_abbr = state_to_abbr.get(state_name)
            if not state_abbr:
                continue

            url = f"{BASE_URL}/{date}?statepostal={state_abbr}&raceTypeId=G&raceId=0&level=ru"

            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code != 200:
                    print(f"[{year}] Failed: {state_abbr} - {county_name} — Status {res.status_code}")
                    continue

                root = ET.fromstring(res.text)
                for ru in root.iter("ReportingUnit"):
                    if ru.attrib.get("Name") == county_name.replace(" County", ""):
                        results = []
                        for c in ru.findall("Candidate"):
                            results.append({
                                "name": f"{c.attrib.get('First')} {c.attrib.get('Last')}",
                                "party": c.attrib.get("Party"),
                                "votes": c.attrib.get("VoteCount")
                            })
                        election_data[year].setdefault(state_abbr, {})[county_name] = results
                        break

            except Exception as e:
                print(f"[{year}] Exception for {state_abbr} - {county_name}: {str(e)}")
                continue

    try:
        output = BytesIO()
        output.write(json.dumps(election_data, indent=2).encode("utf-8"))
        output.seek(0)
        return send_file(output, mimetype="application/json", as_attachment=True, download_name="all_election_results.json")
    except Exception as e:
        return jsonify({"error": f"Error creating file: {str(e)}"}), 500

# Mapping for state names to abbreviations
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

if __name__ == "__main__":
    app.run(debug=True)
