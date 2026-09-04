from __future__ import annotations

import os
import re
import copy
import yaml

from pathlib import Path
from typing import Any, Iterable, Mapping


class LoadDesignConfig:
    """
    YAML-backed config with:
      • dot-key access: cfg["align.gds_file"]
      • ${ENV} and ${dot.keys} interpolation (ENV takes precedence)
      • multi-pass convergence (max_passes)
      • path normalization for keys ending with: *_dir/_path/_file
      • required key validation on dot-keys
    """

    _DOTKEY = re.compile(r"\$\{([^}]+)\}")  # matches ${...} where ... can be dot keys
    _PATH_SUFFIXES = ("_dir", "_path", "_file")

    def __init__(
        self,
        config_path: str | Path,
        *,
        make_abs: bool                  = True,
        base_dir: str | Path | None     = None,
        required: Iterable[str] | None  = None,
    ):
        p = Path(config_path)
        if not p.is_file():
            raise FileNotFoundError(f"Config file not found: {p}")
        self._config_path = p

        with p.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise TypeError(f"Top-level YAML must be a mapping, got {type(loaded).__name__}")

        # Prefer the current working directory as base_dir if not provided
        base = Path(base_dir) if base_dir else Path.cwd()

        # Interpolate + normalize in-place sequence:
        # 1) Interpolate (ENV first, then dot-keys)
        data = self._deep_interpolate(loaded)

        # 2) Normalize path-valued keys to absolute paths
        if make_abs:
            data = self._normalize_paths(data, base)

        self._data: dict[str, Any] = data

        # Validate required dot-keys, if any
        if required:
            missing: list[str] = []
            for k in required:
                try:
                    v = self._get_by_dotkey(self._data, k)
                    if v in (None, ""):
                        missing.append(k)
                except KeyError:
                    missing.append(k)
            if missing:
                raise KeyError(f"Missing required key(s) in {p.name}: {', '.join(missing)}")

    # -------------------- public API --------------------

    def __getitem__(self, key: str) -> Any:
        # allow exact top-level key first (backward compatible)
        if key in self._data:
            return self._data[key]
        # otherwise treat as dot-key
        return self._get_by_dotkey(self._data, key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def get_path(self, key: str) -> Path:
        v = self[key]
        if not isinstance(v, str):
            raise TypeError(f"Value for '{key}' is not a string path (got {type(v).__name__})")
        return Path(v)

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def set(self, dotkey: str, value: Any) -> None:
        """
        Safe in-place set using a.b.c dot-key; creates intermediate mappings as needed.
        """
        parts = dotkey.split(".")
        cur: dict[str, Any] = self._data
        for p in parts[:-1]:
            nxt = cur.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[p] = nxt
            cur = nxt
        cur[parts[-1]] = value

    # -------------------- private helpers --------------------

    @classmethod
    def _is_path_key(cls, key: str) -> bool:
        return key.endswith(cls._PATH_SUFFIXES)

    @classmethod
    def _get_by_dotkey(cls, d: Mapping[str, Any], dotkey: str) -> Any:
        cur: Any = d
        for part in dotkey.split("."):
            if not isinstance(cur, Mapping) or part not in cur:
                raise KeyError(f"Missing key '{dotkey}' (stopped at '{part}')")
            cur = cur[part]
        return cur

    @classmethod
    def _interpolate_string(cls, s: str, lookup: Mapping[str, Any]) -> str:
        """
        Expand ${ENV} from environment and ${dot.key} from the loaded YAML.
        ENV vars take precedence if both exist with the same token.
        """
        def repl(m: re.Match[str]) -> str:
            token = m.group(1)
            if token in os.environ:     # ENV first
                return os.environ[token]
            try:
                v = cls._get_by_dotkey(lookup, token)
            except KeyError:
                return m.group(0)       # leave unresolved for later pass
            return str(v)
        return cls._DOTKEY.sub(repl, s)

    @classmethod
    def _deep_interpolate(cls, data: Any, max_passes: int = 10) -> Any:
        """
        Resolve ${...} across the structure (strings only).
        Runs multiple passes until convergence or max_passes reached.
        """
        result = copy.deepcopy(data)
        for _ in range(max_passes):
            changed = False

            def visit(x: Any) -> Any:
                nonlocal changed
                if isinstance(x, str):
                    y = cls._interpolate_string(x, result)
                    if y != x:
                        changed = True
                    return y
                if isinstance(x, list):
                    out = [visit(i) for i in x]
                    changed = changed or any(a is not b for a, b in zip(out, x, strict=False))
                    return out
                if isinstance(x, dict):
                    out = {k: visit(v) for k, v in x.items()}
                    # structural equality check is costly; rely on string-level changes above
                    return out
                return x

            result = visit(result)
            if not changed:
                break
        return result

    @classmethod
    def _normalize_paths(cls, data: Any, base_dir: Path) -> Any:
        """
        Convert values under keys matching *_dir/_path/_file to absolute paths (if relative).
        """
        if isinstance(data, dict):
            out: dict[str, Any] = {}
            for k, v in data.items():
                norm_v = cls._normalize_paths(v, base_dir)
                if cls._is_path_key(k) and isinstance(norm_v, str):
                    pv = Path(norm_v)
                    if not pv.is_absolute():
                        norm_v = str((base_dir / pv).resolve())
                out[k] = norm_v
            return out
        if isinstance(data, list):
            return [cls._normalize_paths(i, base_dir) for i in data]
        return data


def export2env(
    env_map: dict[str, Any],
) -> None:
    """
    Map config values to environment variables (string-only).
    """
    for k, v in env_map.items():
        if isinstance(v, str):
            os.environ[k] = v
        else:
            raise TypeError(f"Value for {k} must be a string, got {type(v).__name__}")