
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "ASTRO_OS Web UI Online"

@app.route("/status")
def status():
    return jsonify({"status": "running"})
