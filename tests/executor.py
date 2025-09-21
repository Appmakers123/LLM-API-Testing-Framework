import requests
from typing import Tuple, Dict

REQUEST_TIMEOUT_SECS = 30
VERIFY_SSL = False

def do_request(op: Dict) -> Tuple[int, str]:
    method = op["method"]
    url = op["url"]
    headers = op.get("headers", {})
    body = op.get("body", None)
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, params=body if isinstance(body, dict) else None,
                             timeout=REQUEST_TIMEOUT_SECS, verify=VERIFY_SSL)
        else:
            r = requests.request(method, url, headers=headers, json=body,
                                timeout=REQUEST_TIMEOUT_SECS, verify=VERIFY_SSL)
        return r.status_code, r.text
    except Exception as e:
        return -1, f"REQUEST_ERROR: {e}"
