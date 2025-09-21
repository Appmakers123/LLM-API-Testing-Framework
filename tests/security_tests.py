from copy import deepcopy
from typing import List, Dict

def generate_security_tests(op: Dict, spec: Dict) -> List[Dict]:
    test_cases = []
    base_headers = op.get("headers", {}) or {}
    path_spec = spec.get("paths", {}).get(op["path"], {})
    method_spec = path_spec.get(op["method"].lower(), {})
    parameters = method_spec.get("parameters", []) or []

    auth_required = any(
        p.get("in") == "header" and p.get("name").lower() == "x-session-token"
        for p in parameters
    )
    if not auth_required and not method_spec.get("security"):
        return []

    # Preserve the original expected_status for success scenario
    original_expected_status = op.get("expected_status", 200)

    # Test case: Missing x-session-token header (should get 401 Unauthorized)
    if "x-session-token" in base_headers:
        missing_auth = deepcopy(op)
        headers_copy = base_headers.copy()
        headers_copy.pop("x-session-token")
        missing_auth["headers"] = headers_copy
        missing_auth["description"] = "Missing x-session-token header"
        missing_auth["expected_status"] = 401  # Unauthorized expected
        test_cases.append(missing_auth)

    # Test case: Invalid x-session-token header values (expect 401 unauthorized)
    for val in ["", "Bearer invalidtoken", "invalid"]:
        invalid_auth = deepcopy(op)
        headers_copy = base_headers.copy()
        headers_copy["x-session-token"] = val
        invalid_auth["headers"] = headers_copy
        invalid_auth["description"] = f"Invalid x-session-token header value '{val}'"
        invalid_auth["expected_status"] = 401
        test_cases.append(invalid_auth)

    # Test case: Expired token simulation (expect 401)
    expired_auth = deepcopy(op)
    expired_headers = base_headers.copy()
    expired_headers["x-session-token"] = "Bearer expired.token.value"
    expired_auth["headers"] = expired_headers
    expired_auth["description"] = "Expired token in x-session-token header"
    expired_auth["expected_status"] = 401
    test_cases.append(expired_auth)

    # Test case: Malformed token (no 'Bearer' prefix)
    malformed_auth = deepcopy(op)
    malformed_headers = base_headers.copy()
    malformed_headers["x-session-token"] = "thisisnotvalidtoken"
    malformed_auth["headers"] = malformed_headers
    malformed_auth["description"] = "Malformed token without Bearer prefix"
    malformed_auth["expected_status"] = 401
    test_cases.append(malformed_auth)

    # Test case: Wrong token scheme (Basic instead of Bearer)
    wrong_scheme_auth = deepcopy(op)
    wrong_scheme_headers = base_headers.copy()
    wrong_scheme_headers["x-session-token"] = "Basic dXNlcjpwYXNzd29yZA=="
    wrong_scheme_auth["headers"] = wrong_scheme_headers
    wrong_scheme_auth["description"] = "Wrong token scheme (Basic instead of Bearer)"
    wrong_scheme_auth["expected_status"] = 401
    test_cases.append(wrong_scheme_auth)

    # Test case: Injection attempt in token
    injection_auth = deepcopy(op)
    injection_headers = base_headers.copy()
    injection_headers["x-session-token"] = "Bearer <script>alert('xss')</script>"
    injection_auth["headers"] = injection_headers
    injection_auth["description"] = "Injection attempt in x-session-token token"
    injection_auth["expected_status"] = 401
    test_cases.append(injection_auth)

    # Test case: Token with whitespace only
    whitespace_auth = deepcopy(op)
    whitespace_headers = base_headers.copy()
    whitespace_headers["x-session-token"] = "Bearer    "
    whitespace_auth["headers"] = whitespace_headers
    whitespace_auth["description"] = "x-session-token token with whitespace only"
    whitespace_auth["expected_status"] = 401
    test_cases.append(whitespace_auth)

    # Test case: Token with special characters
    special_chars_auth = deepcopy(op)
    special_chars_headers = base_headers.copy()
    special_chars_headers["x-session-token"] = "Bearer !@#$%^&*()_+"
    special_chars_auth["headers"] = special_chars_headers
    special_chars_auth["description"] = "x-session-token token with special characters"
    special_chars_auth["expected_status"] = 401
    test_cases.append(special_chars_auth)

    # Test case: Token with SQL injection attempt
    sql_injection_auth = deepcopy(op)
    sql_injection_headers = base_headers.copy()
    sql_injection_headers["x-session-token"] = "Bearer ' OR '1'='1"
    sql_injection_auth["headers"] = sql_injection_headers
    sql_injection_auth["description"] = "x-session-token token with SQL injection attempt"
    sql_injection_auth["expected_status"] = 401
    test_cases.append(sql_injection_auth)

    # Test case: Empty x-session-token header value explicitly set
    empty_value_auth = deepcopy(op)
    empty_value_headers = base_headers.copy()
    empty_value_headers["x-session-token"] = ""
    empty_value_auth["headers"] = empty_value_headers
    empty_value_auth["description"] = "Empty x-session-token header value"
    empty_value_auth["expected_status"] = 401
    test_cases.append(empty_value_auth)

    return test_cases
