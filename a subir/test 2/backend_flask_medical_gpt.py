import os, json, io, requests, pdfplumber, tempfile, time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
import numpy as np
import faiss                  # index vectorial in‑memory

# ────────────────────────────── Config ────────────────────────────── #
openai.api_key = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY     = os.getenv("SERPAPI_KEY")        # https://serpapi.com/
EMBED_MODEL     = "text-embedding-3-small"        # 512‑dims, barato
K               = 4                               # fragmentos a recuperar

# ─────────────────────── Vector store en memoria ──────────────────── #
VECTOR_DIM = 512
index = faiss.IndexFlatL2(VECTOR_DIM)
stored_chunks = []   # [(id, texto)]

def embed(text: str) -> np.ndarray:
    """Devuelve el embedding OpenAI en np.float32."""
    resp = openai.Embedding.create(model=EMBED_MODEL, input=text[:8191])
    return np.array(resp["data"][0]["embedding"], dtype=np.float32)

# ───────────────────────── Flask app ───────────────────────── #
app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "✅ DR.AI Backend OK – usa /api/ask, /api/upload, /index.html"

# ---------- 1) Upload de documentos ---------- #
@app.route("/api/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Falta archivo"}), 400

    # extraer texto
    text = ""
    ext = (f.filename or "").lower()
    if ext.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(f.read())) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    else:                                       # .txt u otros
        text = f.read().decode("utf-8", errors="ignore")

    # trocear en fragmentos ~ 2 k‑chars
    CHUNK = 2000
    for i in range(0, len(text), CHUNK):
        chunk = text[i:i+CHUNK]
        emb   = embed(chunk)
        index.add(np.array([emb]))
        stored_chunks.append((len(stored_chunks), chunk))

    return jsonify({"status": "ok", "fragments": len(text)//CHUNK + 1})

# ---------- 2) Búsqueda web (SerpAPI) ---------- #
def search_web(query: str, n=5):
    url = "https://serpapi.com/search.json"
    params = {"q": query, "api_key": SERPAPI_KEY, "engine": "google", "num": n}
    data = requests.get(url, params=params, timeout=30).json()
    out  = []
    for r in data.get("organic_results", [])[:n]:
        out.append(f"{r.get('title')} – {r.get('snippet')} ({r.get('link')})")
    return out

# ---------- 3) Recuperar fragmentos de documentos ---------- #
def retrieve_chunks(question: str, top_k=K):
    if index.ntotal == 0:
        return []
    q_emb = embed(question)
    D, I = index.search(np.array([q_emb]), top_k)
    return [stored_chunks[idx][1] for idx in I[0] if idx != -1]

# ---------- 4) Endpoint principal ---------- #
SYSTEM_PROMPT = """Eres DR.AI, un asistente médico riguroso. Usa SIEMPRE la evidencia del bloque CONTEXTO al responder. Cita con (Autor Año) y aclara que no sustituyes consulta médica."""

@app.route("/api/ask", methods=["POST"])
def ask():
    payload = request.json or {}
    user_prompt = payload.get("prompt", "")
    if not user_prompt:
        return jsonify({"error": "prompt vacío"}), 400

    # 1. Web
    web_snippets = search_web(user_prompt, n=5)
    # 2. Docs locales
    doc_snippets = retrieve_chunks(user_prompt)

    contexto = "\n\n".join(
        ["### Web"] + web_snippets +
        ["\n### Documentos"] + doc_snippets
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"CONTEXTO:\n{contexto}"},
        {"role": "user",   "content": user_prompt}
    ]

    completion = openai.ChatCompletion.create(
        model="openai/gpt-3.5-turbo",
        temperature=0.3,
        messages=messages,
    )

    return jsonify({"answer": completion.choices[0].message.content})

# ---------- 5) Historial (sin cambios) ---------- #
HISTORIAL_FILE = "historial_medico.json"

def cargar_historial():
    return json.load(open(HISTORIAL_FILE, encoding="utf-8")) if os.path.exists(HISTORIAL_FILE) else []

def guardar_historial(h):
    json.dump(h, open(HISTORIAL_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

@app.route("/api/historial")
def historial():
    return jsonify(cargar_historial())

@app.route("/api/guardar", methods=["POST"])
def guardar():
    h = cargar_historial(); h.append(request.json); guardar_historial(h)
    return jsonify({"status": "ok"})

# ---------- Frontend (estático) ---------- #
@app.route("/index.html")
def index_html():
    return send_from_directory('.', 'index.html')

# ---------- Main ---------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
