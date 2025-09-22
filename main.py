import argparse
import json as jsonlib
from openapi.loader import load_openapi, pick_base_url
from openapi.operations import collect_operations

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from openapi.example_builder import synthesize_deep_example
from tests.test_generation import (
    recursively_generate_body_tests,
    combine_unique_test_cases,
    generate_body_field_boundary_tests,
)
from tests.executor import do_request
from tests.reporter import write_csv
from tests.header_tests import generate_header_tests_with_mandatory  # UPDATED import
from tests.parameter_tests import generate_parameter_field_tests
from tests.security_tests import generate_security_tests
from tests.test_generation import generate_combinatorial_body_tests
from tests.validator import llm_validate_response_with_kb
from knowledgebase.kb_handler import KnowledgeBase
import json
import time
from typing import Dict, Any, List
from llm_client import chat
from config import (
    OPENAPI_YAML_PATH,
    BASE_URL_OVERRIDE,
    CSV_OUTPUT,
    USE_LLM_VALIDATION,
    KNOWLEDGE_FOLDER
)
import streamlit as st
PERPLEXITY_API_KEY = st.secrets["PERPLEXITY_API_KEY"]

def extract_error_code_mapping(openapi_spec: Dict[str, Any]) -> Dict[str, str]:
    # Your existing code (unchanged)
    mapping = {}
    paths = openapi_spec.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            responses = details.get("responses", {})
            for status_code, resp_detail in responses.items():
                if not isinstance(resp_detail, dict):
                    continue
                content = resp_detail.get("content", {}).get("application/json", {})
                examples = content.get("examples") or {}
                direct_example = content.get("example")
                if direct_example and isinstance(direct_example, dict):
                    error_cd = direct_example.get("errorCd")
                    error_msg = direct_example.get("errorMsg")
                    if error_cd and error_msg:
                        mapping[error_cd] = error_msg
                for example_key, example_obj in examples.items():
                    if not isinstance(example_obj, dict):
                        continue
                    example_val = example_obj.get("value")
                    if example_val and isinstance(example_val, dict):
                        error_cd = example_val.get("errorCd")
                        error_msg = example_val.get("errorMsg")
                        if error_cd and error_msg:
                            mapping[error_cd] = error_msg
    return mapping


FILTER_FILE = None

def run_api_tests(selected_operations: List[Dict] = None):
    print("[INFO] Loading OpenAPI spec...")
    spec = load_openapi(OPENAPI_YAML_PATH)

    with open(OPENAPI_YAML_PATH, "r", encoding="utf-8") as f:
        spec_text = f.read()

    base_url = pick_base_url(spec, BASE_URL_OVERRIDE)
    print(f"[INFO] Base URL: {base_url}")

    error_code_mapping = extract_error_code_mapping(spec)

    all_operations = collect_operations(spec, base_url)

    if selected_operations is None and FILTER_FILE is not None:
        with open(FILTER_FILE, "r") as f:
            filter_paths = jsonlib.load(f)
        selected_operations = [op for op in all_operations if op["path"] in filter_paths]

    operations = selected_operations or all_operations
    print(f"[INFO] Operations selected for testing: {len(operations)}")

    kb = KnowledgeBase(KNOWLEDGE_FOLDER)
    results = []
    error_keywords = ["failed", "error", "validation error", "missing", "empty", "errorCd"]
    mandatory_headers = [

                         ]
    for i, op in enumerate(operations, 1):
        if not op.get("body") and op.get("requestBodySchema"):
            op["body"] = synthesize_deep_example(op["requestBodySchema"])

        recursive_body_tests = recursively_generate_body_tests(
            op, op.get("body", {}), [], op.get("requestBodySchema", {})
        )
        boundary_tests = generate_body_field_boundary_tests(op, spec)
        all_body_tests = combine_unique_test_cases(recursive_body_tests, boundary_tests)
        header_tests = generate_header_tests_with_mandatory(op, spec, mandatory_headers)
        parameter_tests_list = generate_parameter_field_tests(op, spec)
        security_tests_list = generate_security_tests(op, spec)
        combinatorial_tests = generate_combinatorial_body_tests(op, spec, max_comb=2)
        test_variants = combine_unique_test_cases(
            combine_unique_test_cases(
                combine_unique_test_cases(
                    combine_unique_test_cases(all_body_tests, header_tests),
                    parameter_tests_list,
                ),
                security_tests_list,
            ),
            combinatorial_tests,
        )

        print(f"[INFO] Testing operation {i} with {len(test_variants)} test cases...")

        for j, test_op in enumerate(test_variants, 1):
            print(f"[EXEC] {i}.{j} {test_op['method']} {test_op['url']} : {test_op.get('description', '')}")
            start_time = time.time()
            status, body_text = do_request(test_op)
            elapsed = round(time.time() - start_time, 3)
            print(f"Response status: {status}")
            print(f"Response body (truncated): {body_text[:500]}\n")

            relevant_chunks = kb.query(test_op.get("description", "") or test_op["url"])

            actual_error_text = ""
            actual_response_json = None
            try:
                actual_response_json = json.loads(body_text)

                # ✅ Handle dict or list for error text
                if isinstance(actual_response_json, dict):
                    actual_error_text = (
                        actual_response_json.get("errorMsg")
                        or actual_response_json.get("message")
                        or ""
                    )
                elif isinstance(actual_response_json, list) and len(actual_response_json) > 0 and isinstance(actual_response_json[0], dict):
                    actual_error_text = (
                        actual_response_json[0].get("errorMsg")
                        or actual_response_json[0].get("message")
                        or ""
                    )
            except Exception:
                actual_error_text = body_text if isinstance(body_text, str) else ""

            is_error_response = any(kw in actual_error_text.lower() for kw in error_keywords)

            desc = test_op.get("description", "").lower()
            # if is_error_response or ("x-session-token" in desc or "token" in desc or "Invalid Token" in desc):
            #     test_op["expected_status"] = 401
            if is_error_response or ("missing" in desc or "blank" in desc or "invalid" in desc):
                test_op["expected_status"] = 400
            else:
                test_op["expected_status"] = op.get("expected_status", 200)

            expected_error_msg = ""
            error_cd = None

            # ✅ Handle dict or list for error code
            if actual_response_json:
                if isinstance(actual_response_json, dict):
                    error_cd = actual_response_json.get("errorCd")
                elif isinstance(actual_response_json, list) and len(actual_response_json) > 0 and isinstance(actual_response_json[0], dict):
                    error_cd = actual_response_json[0].get("errorCd")

            if error_cd and error_cd in error_code_mapping:
                expected_error_msg = error_code_mapping[error_cd]
            else:
                expected_example_obj = test_op.get("expected_example")
                if expected_example_obj:
                    if isinstance(expected_example_obj, dict):
                        expected_error_msg = (
                            expected_example_obj.get("errorMsg")
                            or expected_example_obj.get("message")
                            or json.dumps(expected_example_obj)
                        )
                    else:
                        expected_error_msg = str(expected_example_obj)

                if not expected_error_msg and test_op.get("description"):
                    expected_error_msg = test_op["description"]

            if USE_LLM_VALIDATION:
                verdict, notes = llm_validate_response_with_kb(
                    spec_text,
                    test_op,
                    status,
                    body_text,
                    relevant_chunks,
                    expected_error_msg,
                    PERPLEXITY_API_KEY,
                )
            else:
                verdict, notes = ("UNSURE", "LLM validation disabled or unavailable")

            test_status = "PASS" if status == test_op.get("expected_status") else "FAIL"

            results.append(
                {
                    "Description": test_op.get("description", ""),
                    "Endpoint": test_op["path"],
                    "Method": test_op["method"],
                    "URL": test_op["url"],
                    "RequestHeaders": json.dumps(test_op.get("headers", {}), ensure_ascii=False),
                    "RequestBody": json.dumps(test_op.get("body", {}), ensure_ascii=False)
                    if test_op.get("body")
                    else "",
                    "ActualStatus": status,
                    "ActualResponseSnippet": body_text if isinstance(body_text, str) else str(body_text),
                    "ExpectedStatus": test_op.get("expected_status"),
                    "ExpectedResponseExample": json.dumps(test_op.get("expected_example") or {}, ensure_ascii=False),
                    "TestStatus": test_status,
                    "LLMVerdict": verdict,
                    "LLMNotes": notes,
                    "ElapsedSecs": elapsed,
                }
            )

    write_csv(CSV_OUTPUT, results)
    print(f"[DONE] Test report saved to: {CSV_OUTPUT}")


def list_apis(operations: List[Dict]) -> None:
    print("\nAvailable APIs:")
    for idx, op in enumerate(operations, 1):
        print(f"{idx}. [{op['method'].upper()}] {op['path']}")


def select_and_run_apis(operations: List[Dict]) -> None:
    list_apis(operations)
    choice = input("Enter 'all' to run all APIs or enter number(s)/path(s) separated by commas: ").strip()

    if choice.lower() == 'all':
        selected_ops = operations
    else:
        selected_ops = []
        inputs = [x.strip() for x in choice.split(",")]
        for inp in inputs:
            if inp.isdigit():
                num = int(inp)
                if 1 <= num <= len(operations):
                    selected_ops.append(operations[num - 1])
            else:
                matches = [op for op in operations if op['path'] == inp]
                selected_ops.extend(matches)

    if not selected_ops:
        print("No valid API(s) selected.")
        return

    print(f"Running {len(selected_ops)} selected API(s) tests...")
    run_api_tests(selected_operations=selected_ops)


def answer_using_kb_and_perplexity(query: str) -> str:
    kb = KnowledgeBase(KNOWLEDGE_FOLDER)
    relevant_chunks = kb.query(query)
    prompt = (
        "You are a helpful assistant. Use the following knowledge base information to answer the question.\n\n"
        f"Context:\n{'---\n'.join(relevant_chunks)}\n\nQuestion:\n{query}\n\nAnswer:"
    )
    response = chat.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def interactive_prompt():
    print("=== Knowledge Base Q&A ===")
    print("Type your question or 'exit' to quit.")
    while True:
        q = input("\nQuestion: ").strip()
        if q.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
        answer = answer_using_kb_and_perplexity(q)
        print("\nAnswer:", answer)






if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tests", action="store_true", help="Run API tests only")
    parser.add_argument("--filter-file", type=str, default=None, help="JSON file with list of API paths to run")
    args = parser.parse_args()

    FILTER_FILE = args.filter_file

    spec = load_openapi(OPENAPI_YAML_PATH)
    base_url = pick_base_url(spec, BASE_URL_OVERRIDE)
    operations = collect_operations(spec, base_url)

    # If filter file provided, load paths and filter operations list
    selected_operations = None
    if FILTER_FILE is not None:
        with open(FILTER_FILE, "r") as f:
            filter_paths = jsonlib.load(f)
        selected_operations = [op for op in operations if op["path"] in filter_paths]

    if args.run_tests:
        run_api_tests(selected_operations=selected_operations or operations)
    else:
        while True:
            print("\nChoose an option:")
            print("1. Run API tests")
            print("2. Select specific APIs to run")
            print("3. Knowledge Base Q&A (interactive)")
            print("4. Exit")
            choice = input("Enter choice number: ").strip()

            if choice == "1":
                run_api_tests(selected_operations=operations)
            elif choice == "2":
                select_and_run_apis(operations)
            elif choice == "3":
                interactive_prompt()
            elif choice == "4":
                print("Exiting. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3 or 4.")
