#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from typing import List, Dict, Any

# Ensure tree-sitter packages are available
try:
    from tree_sitter_languages import get_parser, get_language
except ImportError:
    print("Missing tree-sitter-languages. Run: pip install tree-sitter tree-sitter-languages")
    sys.exit(1)


def run_buf_breaking() -> List[Dict[str, Any]]:
    """Runs buf breaking and returns JSON breaking change records."""
    cmd = [
        "buf", "breaking",
        "v2.bin",
        "--against", "v1.bin",
        "--error-format", "json",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode not in (0, 100):
        print("Buf failed:")
        print(result.stderr)
        sys.exit(result.returncode)

    changes = []

    for line in result.stdout.strip().splitlines():
        if line.strip():
            try:
                changes.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Could not parse Buf JSON: {line}")

    return changes


def extract_impacted_fields(changes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extracts field name and message name from buf breaking change messages."""
    impacted = []
    # Matches patterns like: Field "2" with name "name" on message "Entity" was deleted.
    pattern = re.compile(r'name "([^"]+)".*message "([^"]+)"')

    for change in changes:
        msg_text = change.get("message", "")
        match = pattern.search(msg_text)
        if match:
            field_name = match.group(1)
            message_name = match.group(2)
            impacted.append({
                "field": field_name,
                "message": message_name,
                "type": change.get("type", "BREAKING_CHANGE")
            })
    return impacted


# Semgrep Analysis
def analyze_with_semgrep(impacted_fields: List[Dict[str, str]]):
    """Generates a dynamic Semgrep rule YAML and runs semgrep."""
    if not impacted_fields:
        print("[Semgrep] No broken fields detected to scan.")
        return

    rules = []
    for idx, item in enumerate(impacted_fields):
        field = item["field"]
        # Convert field to PascalCase for C#
        pascal_field = field[0].upper() + field[1:] if field else field

        rules.append({
            "id": f"impacted-field-py-ts-{idx}",
            "languages": ["python", "typescript"],
            "severity": "ERROR",
            "message": f"Usage of deleted/modified Protobuf field '{field}' on '{item['message']}'",
            "patterns": [
                {"pattern-either": [{"pattern": f"$X.{field}"}, {"pattern": f"$X.{field} = $Y"}]}
            ]
        })
        rules.append({
            "id": f"impacted-field-csharp-{idx}",
            "languages": ["csharp"],
            "severity": "ERROR",
            "message": f"Usage of deleted/modified Protobuf field '{pascal_field}' on '{item['message']}'",
            "patterns": [
                {"pattern-either": [{"pattern": f"$X.{pascal_field}"}, {"pattern": f"$X.{pascal_field} = $Y"}]}
            ]
        })

    semgrep_config = {"rules": rules}
    # Turns the python dictionary file semgrep_config into YAML code, then dumps it into .generated_semgrep.yml
    with open(".generated_semgrep.yml", "w") as f:
        import yaml
        yaml.dump(semgrep_config, f)

    print("\n=== Running Semgrep Analysis ===")

    # Run semgrep on the runtimes, using the generated config containing rules and patterns as the context
    subprocess.run(["semgrep", "--config", ".generated_semgrep.yml", "runtimes/"])


# Tree-sitter analysis on the runtimes. Produces information on what fields of the entity were accessed and where.

TREE_SITTER_QUERIES = {
    "python": """
        (attribute
          object: (identifier) @obj
          attribute: (identifier) @field (#eq? @field "{field}"))
    """,
    "typescript": """
        (member_expression
          object: (identifier) @obj
          property: (property_identifier) @field (#eq? @field "{field}"))
    """,
    "csharp": """
        (member_access_expression
          expression: (identifier) @obj
          name: (identifier) @field (#eq? @field "{field}"))
    """
}


def analyze_file_with_treesitter(file_path: str, lang_name: str, target_field: str):
    language = get_language(lang_name)
    parser = get_parser(lang_name)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        return

    tree = parser.parse(bytes(code, "utf8"))
    query_str = TREE_SITTER_QUERIES[lang_name].format(field=target_field)
    query = language.query(query_str)
    captures = query.captures(tree.root_node)

    for node, capture_type in captures:
        if capture_type == "field":
            start_line = node.start_point[0] + 1
            start_col = node.start_point[1]
            print(f"  └─ [Tree-Sitter Impact Match] {file_path}:{start_line}:{start_col} -> Property '{node.text.decode('utf8')}' accessed")


RUNTIME_DIR = "runtimes"

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".cs": "csharp",
}


def run_treesitter_analysis(impacted_fields: List[Dict[str, str]]):
    print("\n=== Running Tree-Sitter AST Analysis ===")

    if not os.path.isdir(RUNTIME_DIR):
        print(f"[Tree-Sitter] Directory not found: {RUNTIME_DIR}")
        return

    runtime_files = []

    for root, _, files in os.walk(RUNTIME_DIR):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in LANGUAGE_EXTENSIONS:
                runtime_files.append(
                    (os.path.join(root, filename), LANGUAGE_EXTENSIONS[ext])
                )

    print(f"[Tree-Sitter] Scanning {len(runtime_files)} source files under {RUNTIME_DIR}/")

    for item in impacted_fields:
        field = item["field"]
        pascal_field = field[0].upper() + field[1:] if field else field

        print(
            f"\nSearching ASTs for accesses to removed field: "
            f"'{field}' (C#: '{pascal_field}')"
        )

        for file_path, lang_name in runtime_files:
            target_field = pascal_field if lang_name == "csharp" else field

            try:
                analyze_file_with_treesitter(
                    file_path,
                    lang_name,
                    target_field,
                )
            except Exception as e:
                print(
                    f"  [Tree-Sitter] Skipping {file_path}: "
                    f"{type(e).__name__}: {e}"
                )


if __name__ == "__main__":
    print("1. Executing buf breaking v2.bin --against v1.bin ...")

    raw_changes = run_buf_breaking()
    impacted = extract_impacted_fields(raw_changes)

    print(f"Found {len(impacted)} impacted field definitions from Buf:")

    for item in impacted:
        print(
            f" - Message: {item['message']} | "
            f"Field: {item['field']} ({item['type']})"
        )

    # Run Analysis
    analyze_with_semgrep(impacted)
    run_treesitter_analysis(impacted)
