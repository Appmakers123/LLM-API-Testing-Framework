from typing import Any, Dict

def synthesize_deep_example(schema: Dict[str, Any]) -> Any:
    if not isinstance(schema, dict):
        return None
    t = schema.get("type")

    if t == "object":
        example_obj = {}
        props = schema.get("properties", {})
        required = schema.get("required", []) or []
        # First, process existing properties with examples or recurse
        for prop_name, prop_schema in props.items():
            if "example" in prop_schema:
                example_obj[prop_name] = prop_schema["example"]
            else:
                example_obj[prop_name] = synthesize_deep_example(prop_schema)
        # Fill any required properties missing in example_obj with safe defaults
        for req in required:
            if req not in example_obj:
                prop_type = props.get(req, {}).get("type", "string")
                example_obj[req] = _default_example_value(prop_type)
        return example_obj

    elif t == "array":
        items = schema.get("items", {})
        return [synthesize_deep_example(items)]

    elif t == "string":
        return schema.get("example", "")

    elif t == "integer":
        return schema.get("example", 0)

    elif t == "number":
        return schema.get("example", 0.0)

    elif t == "boolean":
        return schema.get("example", True)

    else:
        # For unknown types, return None or empty string as fallback
        return schema.get("example", None)


def _default_example_value(field_type: str) -> Any:
    """
    Return a safe default example value based on the JSON schema field type.
    """
    if field_type == "string":
        return ""
    elif field_type == "integer":
        return 0
    elif field_type == "number":
        return 0.0
    elif field_type == "boolean":
        return False
    elif field_type == "array":
        return []
    elif field_type == "object":
        return {}
    else:
        return None
