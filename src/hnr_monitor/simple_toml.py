from __future__ import annotations

from typing import Any, BinaryIO
import ast


def load(fp: BinaryIO) -> dict[str, Any]:
    return loads(fp.read().decode("utf-8"))


def loads(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current = data
    buffered = ""
    bracket_depth = 0

    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).strip()
        if not line:
            continue
        buffered = f"{buffered} {line}".strip() if buffered else line
        bracket_depth += _bracket_delta(line)
        if bracket_depth > 0:
            continue

        statement = buffered
        buffered = ""
        if statement.startswith("[") and statement.endswith("]"):
            current = data
            for part in statement[1:-1].split("."):
                current = current.setdefault(part.strip(), {})
            continue

        if "=" not in statement:
            raise ValueError(f"Invalid TOML statement: {statement}")
        key, value = statement.split("=", 1)
        current[key.strip()] = _parse_value(value.strip())

    if buffered:
        raise ValueError("Unclosed TOML array")
    return data


def _parse_value(value: str) -> Any:
    value = value.rstrip(",").strip()
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        return [_parse_value(part) for part in _split_array(body)]
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith(("\"", "'")):
        return ast.literal_eval(value)
    try:
        return int(value)
    except ValueError:
        return value


def _split_array(body: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for char in body:
        if quote:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"\"", "'"}:
            quote = char
            current.append(char)
        elif char == ",":
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def _strip_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    result: list[str] = []
    for char in line:
        if quote:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"\"", "'"}:
            quote = char
            result.append(char)
        elif char == "#":
            break
        else:
            result.append(char)
    return "".join(result)


def _bracket_delta(line: str) -> int:
    quote: str | None = None
    escaped = False
    delta = 0
    for char in line:
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"\"", "'"}:
            quote = char
        elif char == "[":
            delta += 1
        elif char == "]":
            delta -= 1
    return delta
