import json
from itertools import combinations
import copy
from typing import List, Dict, Any,Union

def deep_set(d: dict, path: list, value: any) -> dict:
    d = copy.deepcopy(d)
    cur = d
    for i, p in enumerate(path):
        is_last = i == len(path) - 1
        # Check if path item is digit indexing a list
        if p.isdigit():
            idx = int(p)
            # Ensure current is a list
            if not isinstance(cur, list):
                # If not list, replace with list
                # This can happen if schema expects list here
                cur_type = type(cur)
                cur_parent = d
                for q in path[:i]:
                    if q.isdigit():
                        q = int(q)
                    cur_parent = cur_parent[q]
                cur_parent[path[i - 1]] = []
                cur = cur_parent[path[i - 1]]

            # Extend list if needed
            while len(cur) <= idx:
                cur.append({} if not is_last else None)
            if is_last:
                cur[idx] = value
            else:
                if not isinstance(cur[idx], dict) and not isinstance(cur[idx], list):
                    cur[idx] = {}
                cur = cur[idx]
        else:
            # path item is dict key
            if not isinstance(cur, dict):
                # Fix structure: replace current with dict
                cur_type = type(cur)
                cur_parent = d
                for q in path[:i]:
                    if q.isdigit():
                        q = int(q)
                    cur_parent = cur_parent[q]
                cur_parent[path[i -1 ]] = {}
                cur = cur_parent[path[i -1]]

            if is_last:
                cur[p] = value
            else:
                if p not in cur or not isinstance(cur[p], (dict, list)):
                    cur[p] = {}
                cur = cur[p]
    return d
def deep_del(d: Union[dict, list], path: List[str]) -> Union[dict, list]:
    """
    Recursively deletes a key/index in a nested dict/list structure given a path.
    Handles missing keys and indexes gracefully.
    """
    d = copy.deepcopy(d)
    cur = d
    for i, p in enumerate(path):
        is_last = (i == len(path) - 1)
        is_index = p.isdigit()

        if is_index:
            idx = int(p)
            if not isinstance(cur, list) or len(cur) <= idx:
                # Path does not exist, nothing to delete
                return d

            if is_last:
                cur.pop(idx)
            else:
                cur = cur[idx]

        else:  # dict key
            if not isinstance(cur, dict) or p not in cur:
                # Path does not exist, nothing to delete
                return d

            if is_last:
                cur.pop(p, None)
            else:
                cur = cur[p]

    return d
def generate_tests_for_field(op: Dict, base_body: Dict, full_path: List[str], field_schema: Dict, is_required: bool) -> List[Dict]:
    tests = []

    # 1. Missing required field
    if is_required:
        missing_case = copy.deepcopy(op)
        missing_case["body"] = deep_del(base_body, full_path)
        missing_case["description"] = f"Missing required body field '{'.'.join(full_path)}'"
        tests.append(missing_case)

    # 2. Blank string (if string type)
    if field_schema.get("type") == "string":
        blank_case = copy.deepcopy(op)
        blank_case["body"] = deep_set(base_body, full_path, "")
        blank_case["description"] = f"Blank string for body field '{'.'.join(full_path)}'"
        tests.append(blank_case)

    # 3. Invalid type test
    invalid_type_values = {
        "string": 12345,
        "integer": "invalid_string",
        "number": "invalid_string",
        "boolean": "not_a_boolean",
        "array": "not_an_array",
        "object": "not_an_object"
    }
    invalid_val = invalid_type_values.get(field_schema.get("type"), None)
    if invalid_val is not None:
        invalid_case = copy.deepcopy(op)
        invalid_case["body"] = deep_set(base_body, full_path, invalid_val)
        invalid_case["description"] = f"Invalid type for body field '{'.'.join(full_path)}'"
        tests.append(invalid_case)

    # 4. Invalid enum value
    enum_vals = field_schema.get("enum")
    if enum_vals and isinstance(enum_vals, list):
        invalid_enum_val = "invalid_enum_val_123"
        if invalid_enum_val not in enum_vals:
            invalid_enum_case = copy.deepcopy(op)
            invalid_enum_case["body"] = deep_set(base_body, full_path, invalid_enum_val)
            invalid_enum_case["description"] = f"Invalid enum value for body field '{'.'.join(full_path)}'"
            tests.append(invalid_enum_case)

    return tests
def recursively_generate_body_tests(op: Dict, base_body: Dict, current_path: List[str], schema: Dict) -> List[Dict]:
    """
    Recursively generate body tests for all nested fields in schema.
    op: base operation dict
    base_body: current request body dict
    current_path: path list to current schema level, e.g. ['templates', '0', 'consentMode']
    schema: current schema dict at this path
    """
    tests = []
    if not isinstance(schema, dict):
        return tests
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for prop, prop_schema in properties.items():
        path = current_path + [prop]
        is_required = prop in required

        # Generate tests for this field
        tests.extend(generate_tests_for_field(op, base_body, path, prop_schema, is_required))

        # Recurse into nested objects
        if prop_schema.get("type") == "object":
            nested_body = base_body.get(prop, {}) if base_body else {}
            tests.extend(recursively_generate_body_tests(op, nested_body, path, prop_schema))

        # Recurse into arrays with object items
        elif prop_schema.get("type") == "array":
            items_schema = prop_schema.get("items", {})
            if items_schema.get("type") == "object":
                arr = base_body.get(prop, []) if base_body else []
                if isinstance(arr, list):
                    for idx, item in enumerate(arr):
                        tests.extend(recursively_generate_body_tests(op, item, path + [str(idx)], items_schema))

    return tests
def generate_combinatorial_body_tests(op: Dict, spec: Dict, max_comb: int = 2) -> List[Dict]:
    """
    Generate tests with combinations of multiple missing or invalid body fields.
    max_comb: maximum number of fields to combine in one test.
    """
    base_body = op.get("body") or {}

    # Parse base_body if it is a JSON string to avoid AttributeError on .keys()
    if isinstance(base_body, str):
        try:
            base_body = json.loads(base_body)
        except Exception:
            base_body = {}

    tests = []
    path_spec = spec.get("paths", {}).get(op["path"], {})
    method_spec = path_spec.get(op["method"].lower(), {})
    rb_spec = method_spec.get("requestBody", {})
    schema = rb_spec.get("content", {}).get("application/json", {}).get("schema", {})
    required_fields = schema.get("required", []) if isinstance(schema, dict) else []

    fields = list(base_body.keys())
    if len(fields) < 2:
        return []

    # Generate combinations of missing required fields
    for r in range(2, min(max_comb + 1, len(fields) + 1)):
        for combo in combinations(fields, r):
            missing_case = copy.deepcopy(op)
            body_copy = copy.deepcopy(base_body)
            for field in combo:
                body_copy.pop(field, None)
            missing_case["body"] = body_copy
            missing_case["description"] = f"Missing multiple body fields {combo}"
            tests.append(missing_case)

    # Generate combinations of invalid types
    invalid_type_map = {
        "string": 12345,
        "integer": "invalid",
        "number": "invalid",
        "boolean": "notabool",
        "array": "notanarray",
        "object": "notanobject",
    }

    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}

    for r in range(2, min(max_comb + 1, len(fields) + 1)):
        for combo in combinations(fields, r):
            invalid_case = copy.deepcopy(op)
            body_copy = copy.deepcopy(base_body)
            for field in combo:
                field_schema = properties.get(field, {})
                t = field_schema.get("type", "string")
                invalid_val = invalid_type_map.get(t, "invalid")
                body_copy[field] = invalid_val
            invalid_case["body"] = body_copy
            invalid_case["description"] = f"Invalid types for multiple body fields {combo}"
            tests.append(invalid_case)

    return tests
def combine_unique_test_cases(cases_1: List[Dict], cases_2: List[Dict]) -> List[Dict]:
    combined = []
    seen = set()
    for c in (cases_1 or []) + (cases_2 or []):
        key = (
            json.dumps(c.get("headers", {}), sort_keys=True),
            json.dumps(c.get("body", {}), sort_keys=True),
        )
        if key not in seen:
            seen.add(key)
            combined.append(c)
    return combined
def generate_body_field_boundary_tests(op: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    tests = []
    base_body = op.get("body") or {}
    rb_spec = spec.get("paths", {}).get(op["path"], {}).get(op["method"].lower(), {}).get("requestBody", {}) or {}
    schema = rb_spec.get("content", {}).get("application/json", {}).get("schema", {}) or {}

    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}

    for field, field_schema in properties.items():
        field_type = field_schema.get("type", "string")
        path = [field]

        if field_type == "string":
            min_len = field_schema.get("minLength")
            max_len = field_schema.get("maxLength")

            if min_len is not None and min_len > 0:
                below_min_case = copy.deepcopy(op)
                below_min_case["body"] = deep_set(base_body, path, "a" * (min_len - 1))
                below_min_case["description"] = f"Below minLength boundary for '{field}'"
                tests.append(below_min_case)

            if max_len is not None:
                above_max_case = copy.deepcopy(op)
                above_max_case["body"] = deep_set(base_body, path, "a" * (max_len + 1))
                above_max_case["description"] = f"Above maxLength boundary for '{field}'"
                tests.append(above_max_case)

        elif field_type in ("integer", "number"):
            minimum = field_schema.get("minimum")
            maximum = field_schema.get("maximum")

            if minimum is not None:
                below_min_case = copy.deepcopy(op)
                val = minimum - 1 if isinstance(minimum, (int, float)) else minimum
                below_min_case["body"] = deep_set(base_body, path, val)
                below_min_case["description"] = f"Below minimum boundary for '{field}'"
                tests.append(below_min_case)

            if maximum is not None:
                above_max_case = copy.deepcopy(op)
                val = maximum + 1 if isinstance(maximum, (int, float)) else maximum
                above_max_case["body"] = deep_set(base_body, path, val)
                above_max_case["description"] = f"Above maximum boundary for '{field}'"
                tests.append(above_max_case)

    return tests
def generate_enhanced_body_tests(op: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    tests = []
    base_body = op.get("body") or {}
    rb_spec = spec.get("paths", {}).get(op["path"], {}).get(op["method"].lower(), {}).get("requestBody", {}) or {}
    schema = rb_spec.get("content", {}).get("application/json", {}).get("schema", {}) or {}

    required_fields = schema.get("required", []) if isinstance(schema, dict) else []
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}

    valid_case = copy.deepcopy(op)
    valid_case["description"] = "Valid request with all required body fields"
    tests.append(valid_case)

    invalid_type_values = {
        "string": 12345,
        "integer": "invalid_string",
        "number": "invalid_string",
        "boolean": "not_a_boolean",
        "array": "not_an_array",
        "object": "not_an_object"
    }

    for field, field_schema in properties.items():
        field_type = field_schema.get("type", "string")
        path = [field]
        is_required = field in required_fields

        if is_required:
            missing_case = copy.deepcopy(op)
            missing_case["body"] = deep_del(base_body, path)
            missing_case["description"] = f"Missing required body field '{field}'"
            tests.append(missing_case)

        if field_type == "string":
            blank_case = copy.deepcopy(op)
            blank_case["body"] = deep_set(base_body, path, "")
            blank_case["description"] = f"Blank string for body field '{field}'"
            tests.append(blank_case)

        invalid_val = invalid_type_values.get(field_type)
        if invalid_val is not None:
            invalid_case = copy.deepcopy(op)
            invalid_case["body"] = deep_set(base_body, path, invalid_val)
            invalid_case["description"] = f"Invalid type for body field '{field}'"
            tests.append(invalid_case)

        enum_vals = field_schema.get("enum")
        if enum_vals and isinstance(enum_vals, list):
            invalid_enum_val = "invalid_enum_val_123"
            if invalid_enum_val not in enum_vals:
                invalid_enum_case = copy.deepcopy(op)
                invalid_enum_case["body"] = deep_set(base_body, path, invalid_enum_val)
                invalid_enum_case["description"] = f"Invalid enum value for body field '{field}'"
                tests.append(invalid_enum_case)

    return tests
def generate_header_field_tests_exhaustive(op: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    tests = []
    base_headers = op.get("headers", {})
    path_spec = spec.get("paths", {}).get(op["path"], {})
    method_spec = path_spec.get(op["method"].lower(), {})
    parameters = method_spec.get("parameters", []) or []

    valid_case = copy.deepcopy(op)
    valid_case["description"] = "Valid request with all required headers"
    tests.append(valid_case)

    for param in parameters:
        if param.get("in") != "header":
            continue
        header_name = param.get("name")
        required = param.get("required", False)

        if required:
            missing_case = copy.deepcopy(op)
            missing_headers = copy.deepcopy(base_headers)
            missing_headers.pop(header_name, None)
            missing_case["headers"] = missing_headers
            missing_case["description"] = f"Missing required header '{header_name}'"
            tests.append(missing_case)

        blank_case = copy.deepcopy(op)
        blank_headers = copy.deepcopy(base_headers)
        blank_headers[header_name] = ""
        blank_case["headers"] = blank_headers
        blank_case["description"] = f"Blank header value for '{header_name}'"
        tests.append(blank_case)

        for invalid_val in ["invalid-value-123", "!!!@@@"]:
            invalid_case = copy.deepcopy(op)
            invalid_headers = copy.deepcopy(base_headers)
            invalid_headers[header_name] = invalid_val
            invalid_case["headers"] = invalid_headers
            invalid_case["description"] = f"Invalid header value '{invalid_val}' for '{header_name}'"
            tests.append(invalid_case)

    return tests
