"""Environment setup for Meeting-Noter."""

import logging
import os
from pathlib import Path

import nltk
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
_initialized = False


def init() -> None:
    """Configure runtime environment (idempotent, safe to call repeatedly)."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    # Load .env file from project root
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    # Store all HuggingFace caches inside the project directory
    hf_cache = project_root / ".cache" / "huggingface"
    os.environ.setdefault("HF_HOME", str(hf_cache))
    os.environ.setdefault("HF_HUB_CACHE", str(hf_cache / "hub"))
    os.environ.setdefault("HF_DATASETS_CACHE", str(hf_cache / "datasets"))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    # Set NLTK lookup path to project cache with manually added tokenizers
    nltk_cache = project_root / ".cache" / "nltk"
    if str(nltk_cache) not in nltk.data.path:
        nltk.data.path.insert(0, str(nltk_cache))

    # Store PyTorch models inside the project directory
    os.environ.setdefault("TORCH_HOME", str(project_root / ".cache" / "torch"))

    logging.getLogger("whisperx.asr").setLevel(logging.ERROR)
    logging.getLogger("pyannote.audio.utils.reproducibility").setLevel(logging.ERROR)
