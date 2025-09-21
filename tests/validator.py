import json
import re
from typing import List, Dict, Tuple

from config import PERPLEXITY_MODEL

try:
    from langchain_perplexity import ChatPerplexity
    from langchain_core.prompts import ChatPromptTemplate
except Exception:
    ChatPerplexity = None
    ChatPromptTemplate = None

def llm_validate_response_with_kb(
    spec_text: str,
    op: Dict,
    actual_status: int,
    actual_body_text: str,
    kb_context: List[str],
    expected_error: str,   # New parameter for expected error message or validation rule
    api_key: str,
    model: str = PERPLEXITY_MODEL,
    use_llm_validation: bool = True
) -> Tuple[str, str]:
    if not use_llm_validation or not ChatPerplexity or not ChatPromptTemplate:
        return "UNSURE", "LLM validation disabled or packages missing."
    try:
        llm = ChatPerplexity(model=model, temperature=0, api_key=api_key)
        kb_text = "\n\nKnowledge Base Context:\n" + "\n---\n".join(kb_context) if kb_context else ""
        prompt_template = ChatPromptTemplate.from_template("""
You are an API testing assistant. Using the OpenAPI spec, observed API response,
expected error message, and related domain knowledge, decide if the response is logically correct.

OpenAPI Spec:

Request:
- Method: {method}
- URL: {url}
- Headers: {headers}
- Body: {body}

Observed Response:
- Status: {status}
- Body: {body_text}

Expected error message or validation rule:
{expected_error}

{kb_text}

Instructions:
1) If the status and response body conform to the spec and domain knowledge, answer PASS.
2) If inconsistencies or errors given domain knowledge, answer FAIL.
3) Otherwise answer UNSURE.
Provide a short rationale.

Return JSON: {{"verdict": "PASS|FAIL|UNSURE", "notes": "explanation"}}
        """)
        prompt = prompt_template.format(
            spec_text=spec_text,
            method=op["method"],
            url=op["url"],
            headers=json.dumps(op.get("headers", {}), ensure_ascii=False),
            body=json.dumps(op.get("body"), ensure_ascii=False) if op.get("body") is not None else "null",
            status=actual_status,
            body_text=actual_body_text[:4000],
            expected_error=expected_error,
            kb_text=kb_text
        )
        resp = llm.invoke(prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            verdict = str(data.get("verdict", "UNSURE")).upper()
            notes = str(data.get("notes", ""))
            if verdict not in ("PASS", "FAIL", "UNSURE"):
                verdict = "UNSURE"
            return verdict, notes
        return "UNSURE", "Unparsed LLM output."
    except Exception as e:
        return "UNSURE", f"LLM error: {e}"
