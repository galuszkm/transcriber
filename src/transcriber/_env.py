"""Environment setup for transcriber.

Configures cache directories (HuggingFace, NLTK, PyTorch) and
suppresses noisy third-party logging.  The ``.env`` file is loaded
by :class:`~transcriber.core.config.TranscriptionConfig` via
pydantic-settings from the current working directory.

Cache location is resolved in the following order:

1. The *cache_dir* argument passed to :func:`init`.
2. ``CACHE_DIR`` environment variable / ``.env`` (via :class:`~transcriber.core.config.TranscriptionConfig`).
3. ``<cwd>/.cache`` (default).
"""

import logging
import os
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)
_initialized = False

#: Resolved cache root, set by :func:`init`.
_cache_dir: Path | None = None


def cache_dir() -> Path:
    """Return the active cache directory.

    Falls back to ``<cwd>/.cache`` if :func:`init` has not been called
    or no explicit path was provided.
    """
    return _cache_dir or _default_cache_dir()


def _default_cache_dir() -> Path:
    """Return the default cache directory (``<cwd>/.cache``)."""
    return Path.cwd() / ".cache"


def init(cache_path: Path | None = None) -> None:
    """Configure runtime environment (idempotent, safe to call repeatedly).

    Args:
        cache_path: Explicit cache root.  Overrides the env var and
            default.  ``None`` keeps the current resolution order.
    """
    global _initialized, _cache_dir

    if cache_path is not None:
        resolved = cache_path.resolve()
    elif "CACHE_DIR" in os.environ:
        resolved = Path(os.environ["CACHE_DIR"]).resolve()
    else:
        resolved = _default_cache_dir()

    if _initialized and resolved == _cache_dir:
        return
    _initialized = True
    _cache_dir = resolved

    root = _cache_dir

    # Store all HuggingFace caches inside the cache directory
    hf_cache = root / "huggingface"
    os.environ["HF_HOME"] = str(hf_cache)
    os.environ["HF_HUB_CACHE"] = str(hf_cache / "hub")
    os.environ["HF_DATASETS_CACHE"] = str(hf_cache / "datasets")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    # Set NLTK lookup path to cache with manually added tokenizers
    nltk_cache = root / "nltk"
    try:
        import nltk

        if str(nltk_cache) not in nltk.data.path:
            nltk.data.path.insert(0, str(nltk_cache))
    except ImportError:
        pass  # nltk not installed (client-only install)
    except Exception as e:
        logger.warning("Failed to set NLTK path: %s", e)

    # Store PyTorch models inside the cache directory
    os.environ["TORCH_HOME"] = str(root / "torch")

    logging.getLogger("whisperx.asr").setLevel(logging.ERROR)
    logging.getLogger("whisperx.vads.pyannote").setLevel(logging.ERROR)
    logging.getLogger("pyannote.audio.utils.reproducibility").setLevel(logging.ERROR)
    logging.getLogger("lightning.pytorch.utilities.migration.utils").setLevel(
        logging.ERROR
    )

    # Suppress noisy third-party warnings (torchcodec, pyannote TF32, etc.)
    warnings.filterwarnings("ignore", message=r"[\s\S]*torchcodec is not installed")
    warnings.filterwarnings("ignore", message=r"std\(\).*degrees of freedom")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", module=r"pyannote\.audio\.utils\.reproducibility")

    # Re-enable TF32 on Ampere+ GPUs. Pyannote disables it for
    # bit-exact reproducibility, but for transcription the ~2x speedup
    # on matmul/convolutions matters more than reproducibility.
    try:
        import torch

        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    except ImportError:
        pass  # torch not installed (client-only install)
    except Exception as e:
        logger.warning("Failed to set TF32 flags: %s", e)
