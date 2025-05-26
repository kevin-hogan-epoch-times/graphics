from flask import Flask, render_template
from flask_socketio import SocketIO
import asyncio
import json
import xml.etree.ElementTree as ET
import aiohttp
import os

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

API_KEY = "your_api_key_here"
BASE_URL = "https://api.ap.org/v2/elections"

state_to_abbr = {
    # ... (same as your existing state_to_abbr dictionary)
}

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on('start_processing')
def handle_start_processing():
    asyncio.run(process_counties())

async def process_counties():
    with open(os.path.join("static", "counties_list.json"), "r") as f:
        counties = json.load(f)

    headers = {"x-api-key": API_KEY}
    async with aiohttp.ClientSession(headers=headers) as session:
        for county in counties:
            state_name = county["State"]
            county_name = county["County"]
            state_abbr = state_to_abbr.get(state_name)
            if not state_abbr:
                continue
            url = f"{BASE_URL}/2020-11-03?statepostal={state_abbr}&raceTypeId=G&raceId=0&level=ru"
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    root = ET.fromstring(text)
                    for ru in root.iter("ReportingUnit"):
                        if ru.attrib.get("Name") == county_name.replace(" County", ""):
                            results = []
                            for c in ru.findall("Candidate"):
                                results.append({
                                    "name": f"{c.attrib.get('First')} {c.attrib.get('Last')}",
                                    "party": c.attrib.get("Party"),
                                    "votes": c.attrib.get("VoteCount")
                                })
                            socketio.emit('county_result', {'county': county_name, 'state': state_name, 'results': results})
                            break
            except Exception as e:
                print(f"Error processing {county_name}, {state_name}: {e}")
            await asyncio.sleep(1)  # Wait for 1 second before processing the next county

if __name__ == "__main__":
    socketio.run(app, debug=True)
