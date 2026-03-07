"""Pre-download models and data into the local cache.

Entry point for ``trans-cache``.  Downloads Whisper models,
alignment models for requested languages, NLTK tokenizer data,
and (optionally) diarization models so that later runs work fully
offline.

Reads the same environment variables as ``transcriber`` /
``trans-server`` (``MODEL``, ``LANGUAGE``, ``DEVICE``,
``DIARIZE``, ``CACHE_DIR``).  CLI arguments take highest priority,
then env vars, then defaults.
"""

from __future__ import annotations

import argparse
import gc
import logging
from pathlib import Path
from typing import Any

import nltk
import whisperx
from whisperx.alignment import DEFAULT_ALIGN_MODELS_HF, DEFAULT_ALIGN_MODELS_TORCH
from whisperx.diarize import DiarizationPipeline

from .. import _env
from ..core.config import VALID_MODEL_SIZES, CacheConfig

# All language codes that have a known alignment model.
_ALL_LANGUAGES: list[str] = sorted(
    set(DEFAULT_ALIGN_MODELS_HF) | set(DEFAULT_ALIGN_MODELS_TORCH)
)

logger = logging.getLogger(__name__)

# HuggingFace repo prefix for faster-whisper CTranslate2 models.
_WHISPER_REPO_PREFIX = "Systran/faster-whisper-"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trans-cache",
        description=(
            "Pre-download models and data for offline use.  "
            "Reads defaults from .env (MODEL, LANGUAGE, DEVICE, "
            "DIARIZE).  CLI flags override."
        ),
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        metavar="SIZE",
        help=f"Whisper model sizes. Choices: {', '.join(sorted(VALID_MODEL_SIZES))}.",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=None,
        metavar="LANG",
        help="ISO language codes for alignment models (default: all).",
    )
    parser.add_argument(
        "--device",
        default=None,
        choices=("cpu", "cuda"),
        help="Device for model loading.",
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        default=None,
        help="Also download diarization models (requires HF_TOKEN).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Override cache directory.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help=(
            "Cache everything: all Whisper model sizes, all languages, "
            "both cpu and cuda, and diarization models."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report what is cached without downloading anything.",
    )
    return parser


def _build_config(args: argparse.Namespace) -> CacheConfig:
    """Build CacheConfig with CLI overrides on top of env/.env defaults."""
    if getattr(args, "all", False):
        return CacheConfig(
            model=",".join(sorted(VALID_MODEL_SIZES)),
            language=",".join(_ALL_LANGUAGES),
            device="cpu",
            diarize=True,
            cache_dir=args.cache_dir,
        )

    overrides: dict[str, Any] = {}
    if args.models is not None:
        overrides["model"] = ",".join(args.models)
    if args.languages is not None:
        overrides["language"] = ",".join(args.languages)
    if args.device is not None:
        overrides["device"] = args.device
    if args.diarize is not None:
        overrides["diarize"] = args.diarize
    if args.cache_dir is not None:
        overrides["cache_dir"] = args.cache_dir
    return CacheConfig(**overrides)


def main() -> int:
    """CLI entry point."""
    args = _build_parser().parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config = _build_config(args)
    _env.init(config.cache_dir)

    # Resolve languages: config.languages returns [] when unset → all.
    resolved_languages = config.languages or _ALL_LANGUAGES

    cache_root = _env.cache_dir()
    logger.info("Cache directory: %s", cache_root)
    logger.info(
        "Config: models=%s  languages=%s  device=%s  diarize=%s",
        ",".join(config.models),
        ",".join(resolved_languages),
        config.device,
        config.diarize,
    )

    if args.check:
        return _check_cache(config, resolved_languages)

    ok = True
    ok &= _download_nltk(cache_root)
    ok &= _download_whisper_models(config.models, config.device)
    ok &= _download_alignment_models(resolved_languages, config.device)
    if config.diarize:
        ok &= _download_diarization(config)

    if ok:
        logger.info("All downloads completed successfully.")
    else:
        logger.error("Some downloads failed — check the log above.")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Check cache
# ---------------------------------------------------------------------------


def _is_hf_cached(hf_hub: Path, repo_id: str) -> bool:
    """Check if a HuggingFace model has downloaded snapshots."""
    dir_name = "models--" + repo_id.replace("/", "--")
    snapshots = hf_hub / dir_name / "snapshots"
    return snapshots.is_dir() and any(snapshots.iterdir())


_OK = "\u2713"
_FAIL = "\u2717"


def _check_cache(config: CacheConfig, resolved_languages: list[str]) -> int:
    """Report what models are present in the cache."""
    cache = _env.cache_dir()
    hf_hub = cache / "huggingface" / "hub"
    all_ok = True

    # NLTK
    punkt = cache / "nltk" / "tokenizers" / "punkt_tab"
    ok = punkt.is_dir()
    all_ok &= ok
    print(f"  {_OK if ok else _FAIL} NLTK punkt_tab")

    # Whisper models
    print()
    for size in config.models:
        repo = f"{_WHISPER_REPO_PREFIX}{size}"
        ok = _is_hf_cached(hf_hub, repo)
        all_ok &= ok
        print(f"  {_OK if ok else _FAIL} Whisper {size}  ({repo})")

    # Alignment models
    print()
    for lang in resolved_languages:
        if lang in DEFAULT_ALIGN_MODELS_TORCH:
            name = DEFAULT_ALIGN_MODELS_TORCH[lang]
            torch_ckpt = cache / "torch" / "hub" / "checkpoints"
            ok = torch_ckpt.is_dir() and any(torch_ckpt.iterdir())
            label = f"align {lang}  ({name}, torchaudio)"
        elif lang in DEFAULT_ALIGN_MODELS_HF:
            repo = DEFAULT_ALIGN_MODELS_HF[lang]
            ok = _is_hf_cached(hf_hub, repo)
            label = f"align {lang}  ({repo})"
        else:
            ok = False
            label = f"align {lang}  (no default model)"
        all_ok &= ok
        print(f"  {_OK if ok else _FAIL} {label}")

    # Diarization
    if config.diarize:
        print()
        pyannote_dirs = (
            sorted(hf_hub.glob("models--pyannote--*")) if hf_hub.is_dir() else []
        )
        ok = len(pyannote_dirs) > 0
        all_ok &= ok
        if ok:
            for d in pyannote_dirs:
                name = d.name.replace("models--", "").replace("--", "/")
                print(f"  \u2713 diarize  ({name})")
        else:
            print("  \u2717 diarize  (pyannote models not found)")

    print()
    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _download_nltk(cache_root: Path) -> bool:
    """Download NLTK punkt tokenizer data."""
    nltk_dir = str(cache_root / "nltk")
    logger.info("Downloading NLTK punkt tokenizer → %s", nltk_dir)
    try:
        nltk.download("punkt_tab", download_dir=nltk_dir, quiet=True)
        return True
    except Exception:
        logger.error("NLTK download failed", exc_info=True)
        return False


def _download_whisper_models(model_sizes: list[str], device: str) -> bool:
    """Download CTranslate2 Whisper models."""
    ok = True
    for size in model_sizes:
        logger.info("Downloading Whisper model: %s", size)
        try:
            model = whisperx.load_model(
                size,
                device=device,
                compute_type="float32",
                language="en",
            )
            del model
            gc.collect()
            logger.info("  ✓ %s", size)
        except Exception:
            logger.error("  ✗ %s", size, exc_info=True)
            ok = False
    return ok


def _download_alignment_models(languages: list[str], device: str) -> bool:
    """Download wav2vec2 alignment models for each language."""
    ok = True
    for lang in languages:
        logger.info("Downloading alignment model: %s", lang)
        try:
            align_model, _ = whisperx.load_align_model(
                language_code=lang,
                device=device,
            )
            del align_model
            gc.collect()
            logger.info("  ✓ %s", lang)
        except ValueError:
            logger.warning("  — no alignment model for '%s' (skipped)", lang)
        except Exception:
            logger.error("  ✗ %s", lang, exc_info=True)
            ok = False
    return ok


def _download_diarization(config: CacheConfig) -> bool:
    """Download pyannote diarization models (requires HF_TOKEN)."""
    if not config.hf_token:
        logger.error(
            "HF_TOKEN not set — cannot download diarization models. "
            "Set HF_TOKEN in your .env or environment."
        )
        return False

    logger.info("Downloading diarization models (pyannote)...")
    try:
        whisperx_cache = _env.cache_dir() / "whisperx"
        _pipeline = DiarizationPipeline(
            token=config.hf_token,
            device=config.device,
            cache_dir=whisperx_cache,
        )
        del _pipeline
        gc.collect()
        logger.info("  \u2713 diarization models")
        return True
    except Exception:
        logger.error("  \u2717 diarization download failed", exc_info=True)
        return False
