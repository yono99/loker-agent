from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional


DEFAULTS: Dict[str, Any] = {
    "search": {
        "keywords": ["data engineer", "backend developer"],
        "locations": ["jakarta", "surabaya", "bandung"],
        "max_per_platform": 30,
    },
    "preferences": {
        "min_score": 7.0,
    },
    "apply": {
        "confirm_before_apply": True,
        "safe_mode": True,
        "enabled_platforms": ["glints", "kalibrr"],
        "delay_seconds": [6, 15],
    },
    "credentials": {
        "glints": {"username": "", "password": ""},
        "kalibrr": {"kb_csrf": "", "cookie": ""},
        "xai_api_key": "",
    },
    "cv": {"path": ""},
    "storage": {"db_dir": "data", "output_dir": "outputs"},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


class Config:
    """Thin dict wrapper over config.json with defaults merged."""

    def __init__(self, data: Dict[str, Any], root: str):
        self._data = data
        self.root = root

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8-sig") as fh:
            raw = json.load(fh)
        merged = _deep_merge(DEFAULTS, raw)
        root = os.path.dirname(os.path.abspath(path))
        return cls(merged, root)

    @classmethod
    def default(cls, root: str) -> "Config":
        return cls(copy.deepcopy(DEFAULTS), root)

    def save(self, path: Optional[str] = None) -> str:
        target = path or os.path.join(self.root, "config.json")
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)
        return target

    def resolve(self, rel: str) -> str:
        return rel if os.path.isabs(rel) else os.path.join(self.root, rel)

    # ---- search ----
    @property
    def keywords(self) -> List[str]:
        return self._data["search"]["keywords"]

    @property
    def locations(self) -> List[str]:
        return self._data["search"]["locations"]

    @property
    def max_per_platform(self) -> int:
        return int(self._data["search"]["max_per_platform"])

    # ---- preferences ----
    @property
    def min_score(self) -> float:
        return float(self._data["preferences"]["min_score"])

    # ---- apply ----
    @property
    def confirm_before_apply(self) -> bool:
        return bool(self._data["apply"]["confirm_before_apply"])

    @property
    def safe_mode(self) -> bool:
        return bool(self._data["apply"]["safe_mode"])

    @property
    def enabled_platforms(self) -> List[str]:
        return list(self._data["apply"]["enabled_platforms"])

    @property
    def delay_seconds(self) -> List[int]:
        return [int(x) for x in self._data["apply"]["delay_seconds"]]

    # ---- credentials ----
    @property
    def xai_api_key(self) -> str:
        return os.environ.get("XAI_API_KEY") or self._data["credentials"]["xai_api_key"]

    @property
    def llm_base_url(self) -> str:
        return os.environ.get("LLM_BASE_URL") or self._data["credentials"].get("llm_base_url", "https://api.x.ai/v1")

    @property
    def glints_username(self) -> str:
        return self._data["credentials"]["glints"]["username"]

    @property
    def glints_password(self) -> str:
        return self._data["credentials"]["glints"]["password"]

    @property
    def kalibrr_cookie(self) -> str:
        return self._data["credentials"]["kalibrr"]["cookie"]

    @property
    def kalibrr_csrf(self) -> str:
        return self._data["credentials"]["kalibrr"]["kb_csrf"]

    # ---- cv & storage ----
    @property
    def cv_path(self) -> Optional[str]:
        p = self._data["cv"].get("path", "")
        return p if p else None

    @property
    def db_dir(self) -> str:
        return self.resolve(self._data["storage"]["db_dir"])

    @property
    def output_dir(self) -> str:
        return self.resolve(self._data["storage"]["output_dir"])
