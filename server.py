from flask import Flask, jsonify, render_template
import threading

app = Flask(__name__, template_folder='.')

_transit_cache = {}
_cache_lock = threading.Lock()


def update_cache(data):
    with _cache_lock:
        global _transit_cache
        _transit_cache = data


@app.route('/')
def index():
    with _cache_lock:
        data = dict(_transit_cache)
    if not data:
        return '<p>Waiting for transit data...</p>', 503
    return render_template('web.html', **data)


@app.route('/data')
def data():
    with _cache_lock:
        return jsonify(_transit_cache)


def start(host='0.0.0.0', port=8080):
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, use_reloader=False),
        daemon=True
    )
    thread.start()
    print(f"🌐 Web server started at http://{host}:{port}")
