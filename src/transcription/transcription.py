import os
import tempfile
import ffmpeg
import yt_dlp
import logging
from faster_whisper import WhisperModel
from dotenv import load_dotenv

load_dotenv()

WHISPER_MODEL = os.getenv("WHISPER_MODEL")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("videolearn")


def download_audio_from_video(video_url: str) -> str:
    """
    Скачивает аудио из видео и возвращает путь к файлу
    """
    tmpdir = tempfile.mkdtemp()
    output_path = os.path.join(tmpdir, "audio.wav")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(tmpdir, 'downloaded'),
        'quiet': True,
        "retries": 10,  # увеличим количество повторов
        "socket_timeout": 30,
        "fragment_retries": 10,
        "nocheckcertificate": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"Failed to download audio from {video_url}: {e}")

    try:
        (
            ffmpeg
            .input(filename)
            .output(output_path, format="wav", acodec="pcm_s16le", ac=1, ar="16k")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg conversion failed: {e.stderr.decode()}")
    
    return output_path


def format_timestamp(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"[{h}:{m}:{s}]"


def transcribe_video(video_url: str, language: str = 'en') -> str:
    """
    Расшифровка видео с таймкодами
    """
    logger.info("Downloading and processing audio")
    audio_path = download_audio_from_video(video_url)

    logger.info("Loading Whisper model")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    logger.info("Transcription")
    segments, _ = model.transcribe(audio_path, language=language)

    lines = []
    for segment in segments:
        end = format_timestamp(segment.end)
        text = segment.text.strip()
        lines.append(f"{end} {text}")

    return "\n".join(lines)