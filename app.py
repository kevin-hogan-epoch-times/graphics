from flask import Flask, render_template, request, send_file
import aiohttp
import asyncio
import xml.etree.ElementTree as ET
import json
from io import BytesIO
import os
from collections import defaultdict

app = Flask(__name__)

API_KEY = "your_api_key_here"
BASE_URL = "https://api.ap.org/v2/elections"

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

@app.route("/batch")
def batch():
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 10))

    with open(os.path.join("static", "counties_list.json"), "r") as f:
        counties = json.load(f)

    selected = counties[offset:offset+limit]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result_data = loop.run_until_complete(fetch_counties(selected))
    loop.close()

    output = BytesIO()
    output.write(json.dumps(result_data, indent=2).encode("utf-8"))
    output.seek(0)

    return send_file(output, mimetype="application/json", as_attachment=True,
                     download_name=f"results_{offset}_to_{offset+limit-1}.json")

async def fetch_counties(counties):
    headers = {"x-api-key": API_KEY}
    results = defaultdict(dict)
    semaphore = asyncio.Semaphore(3)

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for year, date in [("2020", "2020-11-03"), ("2024", "2024-11-05")]:
            for entry in counties:
                state = entry["State"]
                county = entry["County"]
                abbr = state_to_abbr.get(state)
                if not abbr:
                    continue
                url = f"{BASE_URL}/{date}?statepostal={abbr}&raceTypeId=G&raceId=0&level=ru"
                tasks.append(fetch_one(session, semaphore, url, abbr, county, year, results))
            await asyncio.gather(*tasks)
    return results

async def fetch_one(session, semaphore, url, abbr, county, year, results):
    try:
        async with semaphore:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return
                text = await resp.text()
                try:
                    root = ET.fromstring(text)
                except ET.ParseError:
                    return
                for ru in root.iter("ReportingUnit"):
                    if ru.attrib.get("Name") == county.replace(" County", ""):
                        data = []
                        for c in ru.findall("Candidate"):
                            data.append({
                                "name": f"{c.attrib.get('First')} {c.attrib.get('Last')}",
                                "party": c.attrib.get("Party"),
                                "votes": c.attrib.get("VoteCount")
                            })
                        results[year].setdefault(abbr, {})[county] = data
                        break
    except Exception:
        return
