import os
import string
import random
from flask import Flask, request, redirect, render_template, jsonify
from prometheus_flask_exporter import PrometheusMetrics
import redis

app = Flask(__name__)
metrics = PrometheusMetrics(app)  # Wraps entire Flask app and automatically starts tracking every request.

redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))

def get_redis():
    return redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True
    )

def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/shorten", methods=["POST"])
def shorten():
    long_url = request.form.get("url")

    if not long_url:
        return jsonify({"error": "No URL provided"}), 400

    if not long_url.startswith(("http://", "https://")):
        long_url = "https://" + long_url

    r = get_redis()
    short_code = generate_short_code()

    while r.exists(short_code):
        short_code = generate_short_code()

    r.set(short_code, long_url)

    short_url = request.host_url + short_code
    return render_template("index.html", short_url=short_url, original_url=long_url)

@app.route("/<short_code>")
def redirect_url(short_code):
    r = get_redis()
    long_url = r.get(short_code)

    if long_url:
        return redirect(long_url)
    else:
        return render_template("index.html", error=f"Short code '{short_code}' not found"), 404

@app.route("/health")
def health():
    try:
        r = get_redis()
        r.ping()
        return jsonify({"status": "healthy", "redis": "connected", "version": "1.0.1"}), 200
    except Exception:
        return jsonify({"status": "unhealthy", "redis": "disconnected", "version": "1.0.1"}), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)