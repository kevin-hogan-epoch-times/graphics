from flask import Flask, render_template, request, jsonify
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

API_KEY = "4uwfiazjez9koo7aju9ig4zxhr"
ELECTION_DATE = "2020-11-03"
BASE_URL = "https://api.ap.org/v2/elections"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/results")
def results():
    state = request.args.get("state")
    county = request.args.get("county")
    url = f"{BASE_URL}/{ELECTION_DATE}?statepostal={state}&raceTypeId=G&raceId=0&level=ru"
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
