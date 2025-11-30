import aiohttp
import os
import logging
import time
import json
import asyncio

from dotenv import load_dotenv
from fastapi import HTTPException

from src.validation.validator import validate_and_normalize_questions

load_dotenv()

GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE")
GIGACHAT_TOKEN_URL = os.getenv("GIGACHAT_TOKEN_URL")
GIGACHAT_CHAT_URL = os.getenv("GIGACHAT_CHAT_URL")
GIGACHAT_MODEL_NAME = os.getenv("GIGACHAT_MODEL_NAME")
BASE_PROMPT_PATH = os.getenv("BASE_PROMPT_PATH")
PRO_PROMPT_PATH = os.getenv("PRO_PROMPT_PATH")


_token_cache = {"access_token": None, "expires_at": 0}

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("videolearn")


def load_prompt(prompt_path) -> str:
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found at {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

BASE_PROMPT = load_prompt(BASE_PROMPT_PATH)
PRO_PROMPT = load_prompt(PRO_PROMPT_PATH)


async def get_gigachat_token() -> str:
    """Получение и обновление токена GigaChat"""

    # токен ещё жив - возвращаем
    if _token_cache["access_token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["access_token"]

    payload = {"scope": GIGACHAT_SCOPE}

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": "011931f4-080c-40ac-b037-866fabcea4a9",
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                GIGACHAT_TOKEN_URL, headers=headers, data=payload, ssl=False
            ) as resp:
                if resp.status != 200:
                    t = await resp.text()
                    raise HTTPException(
                        status_code=502,
                        detail=f"GigaChat token error: {resp.status} — {t}",
                    )

                data = await resp.json()
                token = data["access_token"]
                expires_in = data.get("expires_in", 1800)

                # сохраняем в кэш
                _token_cache["access_token"] = token
                _token_cache["expires_at"] = time.time() + expires_in - 30

                return token

        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="GigaChat token timeout")

        except aiohttp.ClientError as e:
            raise HTTPException(
                status_code=502, detail=f"GigaChat token network error: {e}"
            )


async def generate_questions_with_gigachat(transcription: str, is_pro_user: bool = False) -> list:
    """Запрос к GigaChat API для генерации вопросов."""
    logger.info("Getting GigaChat token")
    token = await get_gigachat_token()

    prompt = f"{PRO_PROMPT if is_pro_user else BASE_PROMPT} {transcription}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    data = {
        "model": GIGACHAT_MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    logger.info("Generating questions")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GIGACHAT_CHAT_URL, headers=headers, json=data, timeout=300, ssl=False
            ) as resp:

                if resp.status != 200:
                    txt = await resp.text()
                    raise HTTPException(
                        status_code=502,
                        detail=f"GigaChat API error: {resp.status} — {txt}",
                    )

                result = await resp.json()
                content = result["choices"][0]["message"]["content"]

                cleaned = (
                    content.replace("```json", "")
                    .replace("```", "")
                    .replace("*", "")
                    .strip()
                )

                logger.info("Response validation")

                try:
                    parsed = validate_and_normalize_questions(cleaned)
                    return parsed
                except json.JSONDecodeError:
                    return [{"error": "Invalid JSON format", "raw_output": content}]

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="GigaChat API timeout")

    except aiohttp.ClientError as e:
        raise HTTPException(status_code=502, detail=f"GigaChat network error: {e}")
