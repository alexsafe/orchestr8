"""Global console entry point for the repository-local controller."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> int:
    controller = Path(__file__).resolve().parent / ".agent" / "orchestrate.py"
    spec = importlib.util.spec_from_file_location("orchestr8_controller", controller)
    if spec is None or spec.loader is None:
        raise RuntimeError("installed controller assets are unavailable; use the supported editable installation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
