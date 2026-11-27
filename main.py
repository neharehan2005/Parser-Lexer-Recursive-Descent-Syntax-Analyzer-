"""
Driver: lexer.py + parser.py

  python main.py                 checks src.txt
  python main.py myprogram.txt   checks the given file
  python main.py --tokens        also prints the token table

Lexical errors are printed first, then syntax errors. Both stages always run.
"""
import sys
from lexer import tokenize
from parser import Parser, Token

# lexer class_part -> token type the parser expects
CLASS_MAP = {
    "Identifier":     "ID",
    "Data Type":      "DT",
    "Number_literal": "Number_Literal",
    "Text_literal":   "Text_Literal",
    "Truth_literal":  "Truth_Literal",
}

# a lexical error token still goes to the parser, so syntax checking is not
# skipped: a bad identifier is treated as an ID, an unterminated text as a
# text literal. Other error tokens (unknown word, invalid character) are dropped.
ERROR_AS_TOKEN = {
    "ERROR: INVALID_IDENTIFIER":        "ID",
    "ERROR: UNTERMINATED_TEXT_LITERAL": "Text_Literal",
}

LEXICAL_REASONS = {
    "UNDEFINED_WORD":
        "unknown word (not a keyword, data type or truth literal)",
    "INVALID_IDENTIFIER":
        "invalid identifier (must be '$', a letter, then letters/digits, "
        "and the LAST character must be a digit, e.g. $sum1)",
    "INVALID_CHARACTER":
        "invalid character (not part of the language)",
    "UNTERMINATED_TEXT_LITERAL":
        "text literal is missing its closing quote",
}


def lexical_message(t):
    reason = t.class_part.split(":", 1)[1].strip()
    return f"Lexical Error (line {t.line}): {t.lexeme!r} -> {LEXICAL_REASONS.get(reason, reason)}"


def adapt(lex_tokens):
    # convert lexer tokens to parser tokens
    out = []
    for t in lex_tokens:
        cp = t.class_part

        if cp.startswith("ERROR"):
            if cp in ERROR_AS_TOKEN:
                out.append(Token(ERROR_AS_TOKEN[cp], t.lexeme, t.line))
            continue

        # the CFG writes <= and >= as '<' then '='
        if cp in ("<=", ">="):
            out.append(Token(cp[0], cp[0], t.line))
            out.append(Token("=", "=", t.line))
        else:
            out.append(Token(CLASS_MAP.get(cp, cp), t.lexeme, t.line))
    return out


def print_tokens(lex_tokens):
    print(f"{'LINE':<6}{'LEXEME':<28}CLASS PART")
    print("-" * 70)
    for t in lex_tokens:
        print(f"{t.line:<6}{t.lexeme!r:<28}{t.class_part}")
    print()


def analyze(src, show_tokens=False):
    lex_tokens = tokenize(src)
    if show_tokens:
        print_tokens(lex_tokens)

    lex_msgs = [lexical_message(t) for t in lex_tokens
                if t.class_part.startswith("ERROR")]

    try:
        syn_msgs = [str(e) for e in Parser(adapt(lex_tokens)).parse()]
    except RecursionError:
        syn_msgs = ["Syntax Error: program is nested too deeply"]

    return lex_msgs, syn_msgs


def print_report(lex_msgs, syn_msgs):
    if not lex_msgs and not syn_msgs:
        print("Lexical analysis : OK  (no lexical errors)")
        print("Syntax analysis  : OK  (no syntax errors)")
        print("RESULT: ACCEPTED - program is lexically and syntactically correct.")
        return

    print(f"===== LEXICAL ERRORS ({len(lex_msgs)}) =====")
    print("\n".join(lex_msgs) if lex_msgs else "none")
    print()
    print(f"===== SYNTAX ERRORS ({len(syn_msgs)}) =====")
    print("\n".join(syn_msgs) if syn_msgs else "none")
    print()
    print(f"RESULT: REJECTED - {len(lex_msgs)} lexical error(s), "
          f"{len(syn_msgs)} syntax error(s).")


if __name__ == "__main__":
    args = sys.argv[1:]
    show = "--tokens" in args
    files = [a for a in args if a != "--tokens"]
    filename = files[0] if files else "src.txt"

    try:
        with open(filename, encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print(f"ERROR: Source file '{filename}' not found.")
        print("Make sure the .txt file is in the same folder as main.py.")
        sys.exit(1)

    lex_msgs, syn_msgs = analyze(src, show)
    print_report(lex_msgs, syn_msgs)
    sys.exit(1 if (lex_msgs or syn_msgs) else 0)