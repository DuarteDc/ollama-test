from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Memoria temporal por sesión
memoria = defaultdict(lambda: {
    "persona": "",
    "fecha": "",
    "hora": "",
    "numero_persona": 0,
    "vehiculos": "",
    "tipo_visita": "",
    "visitantes": []
})

# Lista de campos en orden
CAMPOS = ["persona", "fecha", "hora", "numero_persona", "vehiculos", "tipo_visita", "visitantes"]

def ask_llm(message):
    prompt = f"""
    Eres un asistente que extrae información para agendar visitas.
    Del siguiente mensaje extrae en JSON:
    - persona
    - fecha (YYYY-MM-DD)
    - hora (HH:MM, y si hay)
    - numero_persona
    - vehiculos (marca, modelo, color, si está)
    - tipo_visita (Entrevista laboral, paquetería, etc)
    - visitantes (lista de objetos con nombre, apellido_paterno, apellido_materno)

    Si falta un dato, devuélvelo como "" o [] o 0 según corresponda.
    Mensaje: "{message}"
    Responde sólo con JSON.
    """

    result = subprocess.run(["ollama", "run", "gemma:2b"], input=prompt, text=True, capture_output=True)
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

    # Procesar mensaje
    info = ask_llm(message)

    if "error" in info:
        return jsonify(info), 500

    # Actualizar memoria
    for campo in CAMPOS:
        if info.get(campo):
            memoria[session_id][campo] = info[campo]

    # Verificar si falta algo
    faltantes = [campo for campo in CAMPOS if not memoria[session_id][campo]]

    if faltantes:
        # Pedir el primer campo faltante
        campo_faltante = faltantes[0]
        mensajes = {
            "persona": "¿A quién vas a visitar?",
            "fecha": "¿En qué fecha será la cita? (YYYY-MM-DD)",
            "hora": "¿A qué hora será la cita? (HH:MM)",
            "numero_persona": "¿Cuántas personas vendrán?",
            "vehiculos": "¿Podrías darme marca, modelo y color del vehículo?",
            "tipo_visita": "¿Cuál es el motivo de la visita?",
            "visitantes": "Por favor, ingresa los nombres completos de los visitantes"
        }
        return jsonify({
            "status": "incompleto",
            "falta": campo_faltante,
            "mensaje": mensajes[campo_faltante]
        })

    # Si ya está completo
    return jsonify({
        "status": "completo",
        "data": memoria[session_id]
    })

if __name__ == '__main__':
    app.run(port=7000, debug=True)
