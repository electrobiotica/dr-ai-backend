# backend_flask_medical_gpt.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, os, json

app = Flask(__name__, static_url_path='')
CORS(app)

OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")  # cargada en Render

@app.route("/")
def root():
    return send_from_directory('.', 'index.html')

# ---------- IA proxy ----------
@app.route("/api/completion", methods=["POST"])
def completion():
    payload = request.get_json()
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )
    return (r.content, r.status_code, {"Content-Type": "application/json"})

# ---------- Historial local en disco (opcional) ----------
HISTORIAL_FILE = "historial_medico.json"
def load_hist(): return json.load(open(HISTORIAL_FILE)) if os.path.isfile(HISTORIAL_FILE) else []
def save_hist(h): json.dump(h, open(HISTORIAL_FILE, "w"), ensure_ascii=False, indent=2)

@app.route("/api/historial")
def historial(): return jsonify(load_hist())

@app.route("/api/guardar", methods=["POST"])
def guardar():
    h = load_hist()
    h.append(request.json)
    save_hist(h)
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
