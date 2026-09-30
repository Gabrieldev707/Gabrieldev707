"""Estado do mundo: serialização canônica, hash e persistência atômica."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

State = dict[str, Any]


def canonical(state: State) -> bytes:
    return json.dumps(
        state, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def state_hash(state: State) -> str:
    return "sha256:" + hashlib.sha256(canonical(state)).hexdigest()


def load_state(path: str | Path) -> State:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_state(path: str | Path, state: State) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def is_internal(state: State, address: str) -> bool:
    return address.lower().endswith("@" + state["company"]["domain"])


def contact(state: State, address: str) -> dict[str, Any] | None:
    address = address.lower()
    return next((c for c in state["contacts"] if c["email"].lower() == address), None)


def render_policies(state: State) -> str:
    return "\n".join(f"- [{p['id']}] {p['text']}" for p in state["policies"])
