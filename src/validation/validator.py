import json
from typing import Any, Dict, List


def normalize_question(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Приводит один вопрос к целевому формату:
    {
      "type": "...",
      "question_text": "...",
      "timecode": "...",
      "points": 0,
      ...
    }
    """
    qtype = raw.get("type") or raw.get("question_type") or "unknown"
    question = {
        "type": qtype,
        "question_text": raw.get("question_text") or raw.get("question") or "",
        "timecode": raw.get("timecode") or raw.get("time") or "",
        "points": raw.get("points", 0),
    }

    # обработка по типам
    if qtype == "multiple_choice":
        options = raw.get("answers") or raw.get("options") or []
        normalized_opts = []
        for o in options:
            if isinstance(o, dict):
                normalized_opts.append({
                    "text": o.get("text", ""),
                    "correct": bool(o.get("correct") or o.get("is_correct")),
                })
            elif isinstance(o, str):
                normalized_opts.append({"text": o, "correct": False})
        question["options"] = normalized_opts

    elif qtype == "open_ended":
        question["answer"] = ""

    elif qtype == "true_false":
        ans = raw.get("answer")
        if isinstance(ans, str):
            ans = ans.lower() in ["true", "yes"]
        question["answer"] = bool(ans)

    elif qtype == "matching":
        pairs = raw.get("pairs") or []
        normalized_pairs = []
        for p in pairs:
            normalized_pairs.append({
                "left": p.get("left", ""),
                "right": p.get("right", ""),
                "correct": bool(p.get("correct", True)),
            })
        question["pairs"] = normalized_pairs

    return question


def validate_and_normalize_questions(data) -> Dict[str, Any]:
    """
    Принимает ответ от Mistral (список или словарь) и возвращает
    гарантированно правильный JSON в формате:
    {"questions": [ ... ]}
    """
    try:
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict) and "questions" in data:
            items = data["questions"]
        elif isinstance(data, list):
            items = data
        else:
            items = []

        normalized = [normalize_question(q) for q in items if isinstance(q, dict)]
        return {"questions": normalized}

    except Exception as e:
        return {"questions": [], "error": f"validation_failed: {e}"}