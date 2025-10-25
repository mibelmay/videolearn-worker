from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

@app.route("/api/generate-questions", methods=["POST"])
def generate_questions():
    try:
        data = request.get_json()
        video_url = data.get("video_url")
        language = data.get("language", "en")

        if not video_url:
            return jsonify({"error": "video_url is required"}), 400

        # --- Расшифровка видео (заглушка) ---
        transcription = [
            {"start": 0, "end": 5, "text": "Welcome to the algebra lesson."},
            {"start": 6, "end": 15, "text": "We will discuss linear equations."},
        ]

        # --- Генерация вопросов через Mistral ---
        mistral_api_key = os.getenv("MISTRAL_API_KEY")
        mistral_url = os.getenv("MISTRAL_API_URL")

        if not mistral_api_key:
            return jsonify({"error": "MISTRAL_API_KEY not set"}), 500

        full_text = "\n".join(f"[{t['start']}-{t['end']}] {t['text']}" for t in transcription)
        prompt = (
            "Generate 5 educational questions for students based on this transcript. "
            "Return JSON array like: [{\"time\":<start>, \"question\":<text>}].\n\n"
            f"Transcript:\n{full_text}"
        )

        headers = {
            "Authorization": f"Bearer {mistral_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": os.getenv("MISTRAL_MODEL", "mistral-medium"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        resp = requests.post(mistral_url, headers=headers, json=payload)
        if resp.status_code != 200:
            return jsonify({"error": f"Mistral API error: {resp.text}"}), 500

        message = resp.json()["choices"][0]["message"]["content"]

        try:
            questions = json.loads(message)
        except json.JSONDecodeError:
            questions = [{"time": 0, "question": message.strip()}]

        return jsonify({"video_url": video_url, "questions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
