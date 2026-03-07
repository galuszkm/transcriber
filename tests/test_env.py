"""Tests for transcriber._env - cache dir resolution and env var setup."""

import os
from pathlib import Path
from unittest.mock import patch

import transcriber._env as env_mod


class TestCacheDir:
    """Cache directory resolution logic."""

    def test_default_is_cwd_cache(self) -> None:
        result = env_mod._default_cache_dir()
        assert result == Path.cwd() / ".cache"

    def test_cache_dir_before_init(self) -> None:
        # When _cache_dir is None, falls back to default
        original = env_mod._cache_dir
        try:
            env_mod._cache_dir = None
            assert env_mod.cache_dir() == env_mod._default_cache_dir()
        finally:
            env_mod._cache_dir = original


class TestInit:
    """init() sets env vars and is idempotent."""

    def test_sets_hf_home(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)
        assert os.environ["HF_HOME"] == str(tmp_path / "huggingface")
        assert os.environ["HF_HUB_CACHE"] == str(tmp_path / "huggingface" / "hub")

    def test_sets_torch_home(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)
        assert os.environ["TORCH_HOME"] == str(tmp_path / "torch")

    def test_idempotent_same_path(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)
        env_mod.init(cache_path=tmp_path)
        # No error; second call is a no-op
        assert env_mod._initialized is True

    def test_reinit_with_different_path(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path / "a")
        env_mod.init(cache_path=tmp_path / "b")
        assert env_mod._cache_dir == (tmp_path / "b").resolve()

    def test_cache_dir_returns_resolved_after_init(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)
        assert env_mod.cache_dir() == tmp_path.resolve()

    def test_nltk_import_error_handled(self, tmp_path: Path) -> None:
        """init() gracefully handles missing nltk."""
        env_mod._initialized = False
        with patch.dict("sys.modules", {"nltk": None}):
            # Should not raise
            env_mod.init(cache_path=tmp_path)
