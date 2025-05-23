from flask import Flask, request, jsonify, render_template
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = "RBQ6bdMu96XgUkPqLwLfgwIZd4xUI0zIeqYq6a5uQqghiBawdio8LqCx9acQZ56S"
BASE_URL = "https://api.ap.org/v2/elections"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/states")
def get_states():
    url = f"{BASE_URL}/metadata/states?apikey={API_KEY}"
    r = requests.get(url)
    return jsonify(r.json())

@app.route("/counties/<state>")
def get_counties(state):
    url = f"{BASE_URL}/metadata/counties/{state}?apikey={API_KEY}"
    r = requests.get(url)
    return jsonify(r.json())

@app.route("/results")
def get_results():
    state = request.args.get("state")
    county = request.args.get("county")
    date = "2024-11-05"
    url = f"{BASE_URL}/results/{date}/president/by-county/{state}/{county}?apikey={API_KEY}"
    r = requests.get(url)
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(debug=True)
