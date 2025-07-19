from flask import Flask, request, render_template
from datetime import datetime

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        pregunta = request.form.get("pregunta", "")
        print(f"[{datetime.now()}] Pregunta recibida: {pregunta}")
    return render_template("index.html")
