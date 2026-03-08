"""Tests for transcriber.server.app - application factory."""

from transcriber.core.config import TranscriptionConfig
from transcriber.server.app import _build_parser, create_app


class TestCreateApp:
    """FastAPI application factory."""

    def test_returns_fastapi_instance(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        app = create_app(cfg)
        assert app.title == "Transcription Service"

    def test_worker_attached_to_state(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        app = create_app(cfg)
        assert app.state.worker is not None
        assert app.state.config is cfg

    def test_router_included(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        app = create_app(cfg)
        paths = [getattr(r, "path", "") for r in app.routes]
        assert "/health" in paths

    def test_sagemaker_routes_registered(self) -> None:
        """SageMaker /ping and /invocations endpoints are present."""
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        app = create_app(cfg)
        paths = [getattr(r, "path", "") for r in app.routes]
        assert "/ping" in paths
        assert "/invocations" in paths


class TestServerParser:
    """Server CLI argument parser."""

    def test_default_host_and_port(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.host == "0.0.0.0"
        assert args.port == 8080

    def test_custom_host_and_port(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--host", "0.0.0.0", "--port", "9000"])
        assert args.host == "0.0.0.0"
        assert args.port == 9000

    def test_pipeline_args_available(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--model", "tiny", "--device", "cpu"])
        assert args.model == "tiny"
        assert args.device == "cpu"
