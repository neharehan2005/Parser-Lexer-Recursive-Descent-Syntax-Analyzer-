"""
Lexical Analyzer
Course: Compiler Construction - Section B
"""

import sys


class Token:
    __slots__ = ("lexeme", "class_part", "line")

    def __init__(self, lexeme, class_part, line):
        self.lexeme = lexeme
        self.class_part = class_part
        self.line = line

    def __repr__(self):
        return f"<{self.line:>3} | {self.lexeme!r:<24} | {self.class_part}>"


# ---------------------------------------------------------------- keywords
# lexeme -> class_part
KEYWORDS = {
    # reserved keywords
    "begin":     "begin",
    "end":       "end",
    "declare":   "declare",
    "as":        "as",
    "set":       "set",
    "to":        "to",
    "array":     "array",
    "of":        "of",
    "show":      "show",
    "ask":       "ask",
    "with":      "with",
    "repeat":    "repeat",
    "while":     "while",
    "if":        "if",
    "otherwise": "otherwise",
    "task":      "task",
    "return":    "return",
    "at":        "at",

    # data types
    "number":    "Data Type",
    "text":      "Data Type",
    "truth":     "Data Type",

    # truth literals
    "true":      "Truth_literal",
    "false":     "Truth_literal",
    "unknown":   "Truth_literal",
}


def _build_trie(words):
    root = {}
    for word, value in words.items():
        node = root
        for ch in word:
            node = node.setdefault(ch, {})
        node["$"] = value
    return root


KEYWORD_TRIE = _build_trie(KEYWORDS)


# --------------------------------------------------- operators and symbols
TWO_CHAR_OPERATORS = {
    "++": "++",
    "--": "--",
    "<=": "<=",
    ">=": ">=",
    "&&": "&&",
    "||": "||",
}

ONE_CHAR_OPERATORS = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "%": "%",
    "<": "<",
    ">": ">",
    "!": "!",
    "=": "=",
}

SPECIAL_CHARACTERS = {
    "{": "{",
    "}": "}",
    "(": "(",
    ")": ")",
    ":": ":",
    ";": ";",
    "?": "?",
    "_": "_",
    "[": "[",
    "]": "]",
    ",": ",",
    ".": ".",      # program ends with: end .
}


# ----------------------------------------------------------- preprocessing
def strip_comment(line):
    # '#' starts a comment, unless it is inside a "text literal"
    in_text = False
    for idx, ch in enumerate(line):
        if ch == '"':
            in_text = not in_text
        elif ch == "#" and not in_text:
            return line[:idx]
    return line


def preprocess(source_text):
    cleaned_lines = []

    for raw_line in source_text.splitlines():
        line = strip_comment(raw_line).strip()
        cleaned_lines.append(line)

    return cleaned_lines


# ------------------------------------------------------- state machines
def scan_word(line, i):
    start = i
    node = KEYWORD_TRIE
    n = len(line)

    while i < n and line[i].isalpha() and line[i] in node:
        node = node[line[i]]
        i += 1

    while i < n and (line[i].isalnum() or line[i] == "_"):
        i += 1

    lexeme = line[start:i]
    value = KEYWORDS.get(lexeme)

    if value is not None:
        return (lexeme, value), i

    return (lexeme, "ERROR: UNDEFINED_WORD"), i


def scan_identifier(line, i):
    # $ letter (letter | digit)*  and the last character must be a digit
    start = i
    n = len(line)

    i += 1  # skip '$'

    if i >= n or not line[i].isalpha():
        return (line[start:i], "ERROR: INVALID_IDENTIFIER"), i

    i += 1
    state = "S2"

    while i < n and (line[i].isalpha() or line[i].isdigit()):
        state = "S3" if line[i].isdigit() else "S2"
        i += 1

    lexeme = line[start:i]

    if state == "S3":
        return (lexeme, "Identifier"), i

    return (lexeme, "ERROR: INVALID_IDENTIFIER"), i


def scan_number(line, i):
    start = i
    n = len(line)

    while i < n and line[i].isdigit():
        i += 1

    # decimal part
    if i + 1 < n and line[i] == "." and line[i + 1].isdigit():
        i += 1
        while i < n and line[i].isdigit():
            i += 1

    return (line[start:i], "Number_literal"), i


def scan_text(line, i):
    start = i
    n = len(line)

    i += 1  # skip opening quote

    while i < n and line[i] != '"':
        i += 1

    if i < n:
        i += 1
        return (line[start:i], "Text_literal"), i

    return (line[start:i], "ERROR: UNTERMINATED_TEXT_LITERAL"), i


def scan_symbol(line, i):
    two = line[i:i + 2]

    if two in TWO_CHAR_OPERATORS:
        return (two, TWO_CHAR_OPERATORS[two]), i + 2

    c = line[i]

    if c in ONE_CHAR_OPERATORS:
        return (c, ONE_CHAR_OPERATORS[c]), i + 1

    if c in SPECIAL_CHARACTERS:
        return (c, SPECIAL_CHARACTERS[c]), i + 1

    return (c, "ERROR: INVALID_CHARACTER"), i + 1


# ------------------------------------------------------------------ driver
def tokenize(source_text):
    tokens = []
    lines = preprocess(source_text)

    for line_no, line in enumerate(lines, start=1):
        i = 0
        n = len(line)

        while i < n:
            c = line[i]

            if c.isspace():
                i += 1
                continue

            if c == "$":
                tok, i = scan_identifier(line, i)
            elif c.isdigit():
                tok, i = scan_number(line, i)
            elif c == '"':
                tok, i = scan_text(line, i)
            elif c.isalpha():
                tok, i = scan_word(line, i)
            else:
                tok, i = scan_symbol(line, i)

            tokens.append(Token(tok[0], tok[1], line_no))

    return tokens


def print_tokens(tokens):
    print(f"{'LINE':<6}{'LEXEME':<28}{'CLASS PART'}")
    print("-" * 70)

    for t in tokens:
        print(f"{t.line:<6}{t.lexeme!r:<28}{t.class_part}")


if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "src.txt"

    try:
        with open(filename, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print(f"ERROR: Source file '{filename}' not found.")
        print("Make sure the .txt file is in the same folder as lexer.py.")
        sys.exit(1)

    print_tokens(tokenize(src))