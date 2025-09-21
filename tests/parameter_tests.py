import json
from copy import deepcopy
from typing import List, Dict

def generate_parameter_field_tests(op: Dict, spec: Dict) -> List[Dict]:
    test_cases = []
    base_body = op.get("body") or {}
    if isinstance(base_body, str):
        try:
            base_body = json.loads(base_body)
        except Exception:
            base_body = {}

    path_spec = spec.get("paths", {}).get(op["path"], {})
    method_spec = path_spec.get(op["method"].lower(), {})
    parameters = method_spec.get("parameters", []) or []

    valid_case = deepcopy(op)
    valid_case["description"] = "Valid request with all parameters"
    test_cases.append(valid_case)

    for param in parameters:
        if param.get("in") not in ("query", "path"):
            continue

        name = param.get("name")
        required = param.get("required", False)
        schema = param.get("schema", {})
        example = schema.get("example", "string")

        if required:
            missing_case = deepcopy(op)
            body_copy = base_body.copy()
            body_copy.pop(name, None)
            missing_case["body"] = body_copy
            missing_case["description"] = f"Missing required parameter '{name}'"
            test_cases.append(missing_case)

        invalid_case = deepcopy(op)
        body_copy = base_body.copy()
        val = body_copy.get(name, example)
        if isinstance(val, str):
            body_copy[name] = 12345
        elif isinstance(val, (int, float)):
            body_copy[name] = "invalid"
        else:
            body_copy[name] = None
        invalid_case["body"] = body_copy
        invalid_case["description"] = f"Invalid type for parameter '{name}'"
        test_cases.append(invalid_case)

    return test_cases
