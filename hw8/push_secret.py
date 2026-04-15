"""One-shot: read .env.hw8 from repo root and push every KEY=VALUE to
the Modal secret `sedge-env`. Replaces any existing value.

Usage:  python3 hw8/push_secret.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    env_path = repo_root / ".env.hw8"
    if not env_path.exists():
        sys.exit(f"Missing {env_path}")

    pairs: list[str] = []
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        pairs.append(f"{key.strip()}={value.strip()}")

    if not pairs:
        sys.exit("No KEY=VALUE pairs found in .env.hw8")

    # Delete old secret (ignore failure if it doesn't exist yet)
    subprocess.run(
        ["modal", "secret", "delete", "sedge-env", "--yes"],
        check=False,
        capture_output=True,
    )

    cmd = ["modal", "secret", "create", "sedge-env", *pairs]
    print(f"Pushing {len(pairs)} keys → Modal secret 'sedge-env'")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
