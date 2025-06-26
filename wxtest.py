from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/greet')
def greet():
    return jsonify(message="Hello from your Python backend on Render!")