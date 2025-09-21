import yaml
import re
from typing import Dict

def load_openapi(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def pick_base_url(spec: Dict, override: str = None) -> str:
    if override:
        return override.rstrip("/")
    servers = spec.get("servers", [])
    if servers and isinstance(servers, list):
        url = (servers[0] or {}).get("url", "").rstrip("/")
        if url:
            return url
    raise ValueError("No base URL found in spec or override.")

def clean_path(path: str) -> str:
    if not path:
        return ""
    return re.sub(r"[*`]", "", path).strip()
