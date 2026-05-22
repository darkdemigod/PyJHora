
from flask import Flask, jsonify
from ai.interpretation_engine import AIInterpretationEngine

app = Flask(__name__)
ai = AIInterpretationEngine()

@app.route("/interpret")
def interpret():
    return jsonify(ai.interpret({}))

@app.route("/ping")
def ping():
    return jsonify({"pong": True})
