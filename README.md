# Parser (Lexer + Recursive-Descent Syntax Analyzer)

**Short description:** The second phase of a mini compiler in Python. A lexer tokenizes a program in a custom language, then a hand-written recursive-descent parser checks it against the language's grammar and reports both lexical and syntax errors with line numbers.

*Compiler Construction project – University of Karachi (UBIT), BS Computer Science.*

---

## What it does

`main.py` runs both stages on a source file and prints a combined report:

1. **Lexical analysis** (`lexer.py`) – splits the source into tokens and flags bad words, identifiers, characters and unterminated text.
2. **Syntax analysis** (`parser.py`) – checks that the token sequence follows the grammar and collects every syntax error it can find in one pass.

Both stages always run, so one execution shows all lexical errors followed by all syntax errors.

## Project structure

```text
Parser/
├── main.py       # driver: runs lexer, adapts tokens, runs parser, prints report
├── lexer.py      # DFA / state-machine lexer with keyword trie
├── parser.py     # recursive-descent parser with error recovery
├── src.txt       # a correct program (should be ACCEPTED)
└── errors.txt    # a program with lexical AND syntax errors (should be REJECTED)
```

## Requirements

Python 3.8+. No external libraries.

## How to run

```bash
python main.py                  # checks src.txt
python main.py errors.txt       # checks another file
python main.py --tokens         # also prints the token table
```

Exit code is `0` if the program is accepted and `1` if any error is found.

## The language

Every program has the form:

```text
begin {
    <statements>
}
end .
```
(note the final `.` after `end`).

| Statement | Example |
|---|---|
| Declaration | `declare $a1 as number set to 10` |
| Array declaration | `declare $arr1 as number array of 3 set $arr1 to [1, 2, 3]` |
| Assignment | `set $a1 to ($a1 + 5) * 2` |
| Array element assignment | `set $arr1 at 0 to 99` |
| Input | `ask $a1 with "Enter a number: "` |
| Output | `show $a1`, `show $arr1 at 1`, `show "big" if $a1 >= 10` |
| Loop | `repeat while $a1 > 0 { show $a1  $a1-- }` (body must end with `$id++` or `$id--`) |
| Function | `task $add1($x1, $y1) { ... return $r1 }` |
| Function call / increment | `$add1(2, 3)`, `$a1++` |

Types: `number`, `text`, `truth` (`true`, `false`, `unknown`). Identifiers: `$` + letter + letters/digits, **ending in a digit** (`$sum1`). Comments start with `#` and may appear anywhere outside a text literal.

Expression precedence (lowest to highest): assignment `=` → `||` → `&&` → `!` → `< > <= >=` → `+ -` → `* / %` → postfix `++ --` → literals, identifiers, `( )`.

## How it works

- **Lexer → parser bridge (`main.py`)**: `adapt()` maps lexer class parts to parser token types (`Identifier` → `ID`, `Data Type` → `DT`, …). `<=` and `>=` are split into `<`/`>` + `=` because the grammar defines them that way. Identifiers with errors and unterminated text are still passed on as `ID` / `Text_Literal`, so syntax checking continues instead of stopping at the first lexical error.
- **Parser (`parser.py`)**: one method per grammar rule (`start`, `statements`, `statement`, `expression`, …) using one-token lookahead, with a few extra lookaheads where rules share a prefix (e.g. `set … to` vs. `set $id to [`).
- **Error handling**:
  - `match()` records a *missing token* error and continues as if the token were present.
  - Only one error is reported per token, so a single mistake does not cascade.
  - `skip_junk()` performs panic-mode recovery, skipping to the next closer (`}`, `end`, `return`) or to a statement starting on a later line.
  - Missing tokens are reported on the line where the previous token ended.

## Sample output (`python main.py errors.txt`)

```text
===== LEXICAL ERRORS (4) =====
Lexical Error (line 6): '$b' -> invalid identifier (...)
Lexical Error (line 8): '@' -> invalid character (not part of the language)
Lexical Error (line 12): '"hello' -> text literal is missing its closing quote
Lexical Error (line 14): 'foo' -> unknown word (...)

===== SYNTAX ERRORS (5) =====
Syntax Error (line 6): Missing token: expected 'as' but found data type 'number'
Syntax Error (line 10): Unexpected token number literal '5': expected 'to' or 'at' after 'set'
Syntax Error (line 18): Unexpected token '}': expected a statement or the loop update (...)
Syntax Error (line 20): Missing token: expected ')' but found 'task'
Syntax Error (line 23): Missing token: expected 'return' but found '}'

RESULT: REJECTED - 4 lexical error(s), 5 syntax error(s).
```

For a valid program (`python main.py`):

```text
Lexical analysis : OK  (no lexical errors)
Syntax analysis  : OK  (no syntax errors)
RESULT: ACCEPTED - program is lexically and syntactically correct.
```

## Technologies / concepts

Python 3 · DFA / state machines · trie · context-free grammar · recursive-descent (top-down) parsing · panic-mode error recovery

## License

Educational use.
