"""Allow running the package with ``python -m transcriber``."""

from .cli.app import main

raise SystemExit(main())
