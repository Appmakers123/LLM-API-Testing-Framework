from copy import deepcopy
from typing import List, Dict

def generate_header_tests_with_mandatory(op: Dict, spec: Dict, mandatory_headers: List[str]) -> List[Dict]:
    test_cases = []
    base_headers = op.get("headers", {}) or {}

    # Normalize mandatory headers lowercase for case-insensitive checks
    mandatory_headers_lower = [h.lower() for h in mandatory_headers]

    for hdr in base_headers.keys():
        valid_mandatory_headers = {h: base_headers[h] for h in mandatory_headers if h in base_headers}

        if hdr.lower() in mandatory_headers_lower:
            # Missing mandatory header test case
            missing_case = deepcopy(op)
            headers_copy = dict(valid_mandatory_headers)
            headers_copy.pop(hdr, None)  # remove only tested header
            # Add other non-mandatory headers except tested header
            for h in base_headers:
                if h.lower() != hdr.lower() and h.lower() not in mandatory_headers_lower:
                    headers_copy[h] = base_headers[h]
            missing_case["headers"] = headers_copy
            missing_case["description"] = f"Missing mandatory header '{hdr}'"
            test_cases.append(missing_case)

            # Invalid mandatory header test case
            invalid_case = deepcopy(op)
            headers_copy = dict(valid_mandatory_headers)
            headers_copy[hdr] = "InvalidValue!@#"
            for h in base_headers:
                if h.lower() != hdr.lower() and h.lower() not in mandatory_headers_lower:
                    headers_copy[h] = base_headers[h]
            invalid_case["headers"] = headers_copy
            invalid_case["description"] = f"Invalid mandatory header '{hdr}'"
            test_cases.append(invalid_case)

        else:
            # Optional header missing test case, keep mandatory headers intact
            missing_case = deepcopy(op)
            headers_copy = dict(valid_mandatory_headers)
            for h in base_headers:
                if h.lower() != hdr.lower() and h.lower() not in mandatory_headers_lower:
                    headers_copy[h] = base_headers[h]
            missing_case["headers"] = headers_copy
            missing_case["description"] = f"Missing optional header '{hdr}'"
            test_cases.append(missing_case)

            # Optional header invalid test case
            invalid_case = deepcopy(op)
            headers_copy = dict(valid_mandatory_headers)
            for h in base_headers:
                if h.lower() != hdr.lower() and h.lower() not in mandatory_headers_lower:
                    headers_copy[h] = base_headers[h]
            headers_copy[hdr] = "InvalidValue!@#"
            invalid_case["headers"] = headers_copy
            invalid_case["description"] = f"Invalid optional header '{hdr}'"
            test_cases.append(invalid_case)

    return test_cases
