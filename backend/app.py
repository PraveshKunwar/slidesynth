from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def get_home():
    return "bro you're home right now"

@app.route('/api/health')
def get_data():
    return jsonify({"rest": "health data bro"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
