from typing import List, Dict, Any
from openapi.loader import pick_base_url, clean_path
from openapi.example_builder import synthesize_deep_example
# from config import legalEntityId, configId, txn, tenant_id, x_session_token, userId, scopeLevel, roleId, purposeId, \
#     dataTypeId, businessId


def first_example_from_media(media_obj: Dict[str, Any]) -> Any:
    if not media_obj:
        return None
    if "example" in media_obj:
        return media_obj["example"]
    examples = media_obj.get("examples")
    if isinstance(examples, dict):
        for _, v in examples.items():
            if isinstance(v, dict) and "value" in v:
                return v["value"]
    schema = media_obj.get("schema", {})
    if "example" in schema:
        return schema["example"]
    return None

def collect_operations(spec: Dict[str, Any], base_url: str) -> List[Dict[str, Any]]:
    operations = []
    paths = spec.get("paths", {})
    for raw_path, methods in paths.items():
        path = clean_path(raw_path)
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch", "head", "options"):
                continue

            url = f"{base_url}{path}"
            headers = {}

            # Add header parameters from spec (may include dummy/example values)
            for p in details.get("parameters", []) or []:
                if p.get("in") == "header":
                    name = p.get("name")
                    example = p.get("schema", {}).get("example", "string")
                    headers[name] = example

            # Headers from config always overwrite or add
            # if x_session_token:
            #     headers["x-session-token"] = f"Bearer {x_session_token}"
            #
            # if tenant_id:
            #     headers["tenant-id"] = tenant_id
            #     headers["tenant-id"] = tenant_id  # If needed by API, else remove
            #
            # if txn:
            #     headers["txn"] = txn
            #
            # if legalEntityId:
            #     headers["legalEntityId"] = legalEntityId
            #
            # if configId:
            #     headers["configId"] = configId
            #
            # if businessId:
            #     headers["businessId"] = businessId
            #
            # if dataTypeId:
            #     headers["dataTypeId"] = dataTypeId
            #
            # if purposeId:
            #     headers["purposeId"] = purposeId
            #
            # if roleId:
            #     headers["roleId"] = roleId
            #
            # if scopeLevel:
            #     headers["scopeLevel"] = scopeLevel
            #
            # if userId:
            #     headers["configId"] = userId

            # Content-Type & body
            schema = None
            if details.get("requestBody"):
                headers.setdefault("Content-Type", "application/json")
                rb_content = details.get("requestBody", {}).get("content", {}).get("application/json", {})
                schema = rb_content.get("schema", {})
                body = synthesize_deep_example(schema)
            else:
                body = None

            # Extract expected response example and status with prioritized codes
            responses = details.get("responses", {}) or {}
            expected_status = None

            # Prioritize success codes (200-series)
            for code in ("200", "201", "204"):
                if code in responses:
                    expected_status = code
                    break

            # If no success code found, prioritize error codes (400-series)
            if not expected_status:
                for code in ("400", "401", "404"):
                    if code in responses:
                        expected_status = code
                        break

            # Fallback: use the first available response status code
            if not expected_status and responses:
                expected_status = list(responses.keys())[0]

            exp_content = responses.get(expected_status, {}).get("content", {})
            expected_example = first_example_from_media(exp_content.get("application/json", {}))

            # Debug print headers
            print(f"[DEBUG] Headers for {method.upper()} {url}: {headers}")
            print(f"[DEBUG] Expected status: {expected_status}, expected example: {expected_example}")

            operations.append({
                "method": method.upper(),
                "url": url,
                "path": path,
                "headers": headers,
                "body": body,
                "requestBodySchema": schema if details.get("requestBody") else None,
                "responses": responses,
                "expected_status": int(expected_status) if expected_status else None,
                "expected_example": expected_example,
            })
    return operations
