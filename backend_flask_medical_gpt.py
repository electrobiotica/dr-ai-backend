from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

HISTORIAL_FILE = "historial_medico.json"

def cargar_historial():
    if not os.path.exists(HISTORIAL_FILE):
        return []
    with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_historial(historial):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)

@app.route("/")
def home():
    return "✅ DR.AI Backend funcionando correctamente. Usa /api/historial, /api/guardar o /index.html"

@app.route("/api/historial", methods=["GET"])
def obtener_historial():
    return jsonify(cargar_historial())

@app.route("/api/guardar", methods=["POST"])
def guardar():
    datos = request.json
    historial = cargar_historial()
    historial.append(datos)
    guardar_historial(historial)
    return jsonify({"status": "ok", "mensaje": "Historial guardado"})

@app.route("/index.html")
def servir_index():
    return send_from_directory('.', 'index.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
