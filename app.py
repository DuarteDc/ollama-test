from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
from collections import defaultdict

app = Flask(__name__)
CORS(app)

memoria = defaultdict(lambda: {
    "persona": "",
    "fecha": "",
    "hora": "",
    "numero_persona": 0,
    "vehiculos": "",
    "tipo_visita": "",
    "visitantes": []
})

CAMPOS = ["persona", "fecha", "hora", "numero_persona", "vehiculos", "tipo_visita", "visitantes"]

def ask_llm(message, faltantes=None):
    prompt = f"""
    Eres un asistente de agenda de visitas. 
    Debes:
    1. Extraer en formato JSON los siguientes campos del mensaje:
       - persona
       - fecha (YYYY-MM-DD)
       - hora (HH:MM, si está)
       - numero_persona
       - vehiculos (marca, modelo, color, si está)
       - tipo_visita (Entrevista laboral, paquetería, etc)
       - visitantes (lista de objetos con nombre, apellido_paterno, apellido_materno)
    2. Si falta un dato, devuélvelo como "" o [] o 0.
    3. Si se te da la lista de campos faltantes, genera también un campo extra `"pregunta"` con una pregunta natural y amistosa para pedir **solo el primer dato que falte**.
    
    Mensaje del usuario: "{message}"
    Campos faltantes (si aplica): {faltantes if faltantes else "Ninguno"}
    
    Responde SOLO con JSON.
    """

    result = subprocess.run(
        ["ollama", "run", "mistral:7b-instruct"], 
        input=prompt,
        text=True,
        capture_output=True
    )

    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": "No pude parsear la respuesta", "raw": result.stdout}

@app.route("/agendar", methods=["POST"])
def agendar():
    data = request.json
    session_id = data.get("session_id")
    message = data.get("message", "")

    if not session_id:
        return jsonify({"error": "Falta session_id"}), 400
    if not message:
        return jsonify({"error": "No se envió mensaje"}), 400


    info = ask_llm(message)

    if "error" in info:
        return jsonify(info), 500


    for campo in CAMPOS:
        if info.get(campo):
            memoria[session_id][campo] = info[campo]


    faltantes = [campo for campo in CAMPOS if not memoria[session_id][campo]]

    if faltantes:
    
        pregunta_info = ask_llm(message, faltantes=faltantes)
        pregunta = pregunta_info.get("pregunta", f"Por favor, ingresa {faltantes[0]}.")

        return jsonify({
            "status": "incompleto",
            "falta": faltantes[0],
            "mensaje": pregunta
        }), 400


    return jsonify({
        "status": "completo",
        "data": memoria[session_id]
    })

if __name__ == '__main__':
    app.run(port=7000, debug=True)
