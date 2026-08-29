"""Tiny s-expression reader, enough for KiCad symbol and footprint files."""

from __future__ import annotations


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            tokens.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                elif text[j] == '"':
                    break
                else:
                    buf.append(text[j])
                    j += 1
            tokens.append('"' + "".join(buf))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def parse(text: str):
    """Parse into nested lists; strings keep a leading double quote marker."""
    tokens = tokenize(text)
    pos = 0

    def read():
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            out = []
            while tokens[pos] != ")":
                out.append(read())
            pos += 1
            return out
        if tok == ")":
            raise ValueError("unbalanced s-expression")
        return tok

    result = read()
    if pos != len(tokens):
        raise ValueError("trailing tokens after s-expression")
    return result


def atom(value) -> str:
    """String value of an atom, stripping the string marker."""
    return value[1:] if isinstance(value, str) and value.startswith('"') else value


def find_all(node, tag: str):
    return [child for child in node if isinstance(child, list) and child and child[0] == tag]


def find_one(node, tag: str):
    matches = find_all(node, tag)
    return matches[0] if matches else None
