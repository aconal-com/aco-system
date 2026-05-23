"""
JSON extraction utilities for parsing LLM responses.

LLMs return JSON wrapped in explanatory text, code blocks, or partial markdown.
These helpers extract the actual JSON object or array by matching brace/bracket depth,
avoiding the common bug of truncating at the first } or ] inside a string.
"""
import json
import re
from typing import Union


def extract_json(response: str) -> Union[dict, list, None]:
    """
    Extract the first complete JSON object or array from an LLM response.

    Uses depth counting to find the matching closing bracket for the outermost
    opening bracket, so content like {"key": "value with } inside"} is handled
    correctly (the } inside the string doesn't prematurely close the object).

    Handles:
    - Text that starts with { } (JSON objects)
    - Text that starts with [ ] (JSON arrays)
    - Markdown code fences around JSON
    - LLM reasoning/thinking blocks before JSON
    - Leading text before JSON (HTTP headers, explanatory text)

    Returns the parsed JSON, or None if no valid JSON found.
    """
    text = response.strip()
    if not text:
        return None

    # Step 1: Strip LLM reasoning/thinking blocks that may contain [ ] or { } chars
    # Run multiple passes until no more tags remain (handles nested/sequential blocks)
    prev_text = None
    while prev_text != text:
        prev_text = text
        # Strip paired tags: <...>content</...> or <.../> (self-closing)
        text = re.sub(r'<[^/>]*(?:/>|>.*?</[^/>]*>)', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Strip bare MiniMax-style thinking block markers (closing tags without opening tags)
        text = re.sub(r'〗.*?『', '', text, flags=re.DOTALL)  # Unicode bracket thinking
        text = re.sub(r'OKEN', '', text)  # bare bracket thinking (MiniMax-style separator)
        text = re.sub(r'</?[a-zA-Z][^>]*>', '', text)  # bare closing tags like </reasoning>, </think>
        text = text.strip()

    # NOTE: Do NOT use regex to strip "thinking blocks" — it can destroy JSON arrays like []
    # The thinking block removal happens in the while loop above using tag-based stripping only.


    # Determine what kind of JSON structure we're looking for.
    # This matters because { inside strings should not close an array [ ... ].
    first_char = text[0]
    if first_char == '[':
        opening_char, closing_char = '[', ']'
        start = 0
    elif first_char == '{':
        opening_char, closing_char = '{', '}'
        start = 0
    elif first_char == '`':
        # Embedded in markdown code fences — find first { or [
        obj_start = text.find('{')
        arr_start = text.find('[')
        if obj_start == -1 and arr_start == -1:
            return None
        if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
            opening_char, closing_char = '[', ']'
            start = arr_start
        else:
            opening_char, closing_char = '{', '}'
            start = obj_start
    else:
        # Embedded in text — find first { or [ and count from there
        obj_start = text.find('{')
        arr_start = text.find('[')
        if obj_start == -1 and arr_start == -1:
            return None
        if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
            opening_char, closing_char = '[', ']'
            start = arr_start
        else:
            opening_char, closing_char = '{', '}'
            start = obj_start

    # Depth-counting scan to find the matching closing bracket
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == '\\':
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == opening_char:
            depth += 1
        elif ch == closing_char:
            depth -= 1
            if depth == 0:
                # Found matching closing bracket for the outermost structure
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

                # Try stripping markdown code fences
                stripped = candidate.strip()
                if stripped.startswith('```'):
                    stripped = re.sub(r'^```[a-zA-Z]*\s*', '', stripped, flags=re.IGNORECASE)
                    stripped = re.sub(r'\s*```$', '', stripped)
                    stripped = stripped.strip()
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass

                return None

    return None


def extract_first_json_object(response: str) -> dict:
    """
    Extract the first JSON object from an LLM response.

    Returns the first dict in an array, or the dict itself.
    Returns empty dict on failure (never raises).
    """
    result = extract_json(response)
    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        if result and isinstance(result[0], dict):
            return result[0]
    return {}


def parse_llm_json(response: str, default: dict = {}) -> dict:
    """
    Parse LLM JSON response safely, returning default on failure.
    """
    result = extract_json(response)
    if isinstance(result, dict):
        return result
    return default
