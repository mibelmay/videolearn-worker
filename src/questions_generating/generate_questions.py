import aiohttp
import os
import logging
import json
import asyncio

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL =  os.getenv("MISTRAL_API_URL")
MISTRAL_MODEL_NAME = os.getenv("MISTRAL_MODEL")
BASE_PROMPT_PATH = os.getenv("BASE_PROMPT_PATH")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("videolearn")


def load_base_prompt() -> str:
    if not os.path.exists(BASE_PROMPT_PATH):
        raise FileNotFoundError(f"Prompt file not found at {BASE_PROMPT_PATH}")
    with open(BASE_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()
    

BASE_PROMPT = load_base_prompt()


async def generate_questions_with_mistral(
    transcription: str
) -> list:
    """Отправка запроса к API Mistral для генерации вопросов"""
    prompt = f"{BASE_PROMPT} {transcription}"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MISTRAL_MODEL_NAME, 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(MISTRAL_API_URL, headers=headers, json=data, timeout=300) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Mistral API error: {resp.status} - {text}")
                    raise HTTPException(status_code=502, detail="Mistral API error")

                result = await resp.json()
                content = result["choices"][0]["message"]["content"]

                cleaned = (
                    content.replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

                try:
                    parsed = json.loads(cleaned)
                    return parsed
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from Mistral")
                    return [{"error": "Invalid JSON format", "raw_output": content}]
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Mistral API timeout")
    except aiohttp.ClientError as e:
        logger.error(f"Network error: {e}")
        raise HTTPException(status_code=502, detail="Network error to Mistral")
