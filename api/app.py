from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import os

from src.transcription.transcription import transcribe_video
from src.questions_generating.generate_questions import generate_questions_with_mistral

app = FastAPI(title="VideoLearn")


class VideoRequest(BaseModel):
    video_url: str
    language: str = "en"

@app.post("/api/generate-questions")
async def generate_questions(req: VideoRequest):
    loop = asyncio.get_event_loop()
    transcription = await loop.run_in_executor(None, transcribe_video, req.video_url, req.language)
    questions = await generate_questions_with_mistral(transcription)
    return questions