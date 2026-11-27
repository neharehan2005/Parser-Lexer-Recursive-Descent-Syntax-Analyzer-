
class Token:
    def __init__(self, type_, value=None, line=1):
        self.type = type_
        self.value = value if value is not None else type_
        self.line = line

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r})"


# names used in error messages
TYPE_NAMES = {
    "ID": "identifier",
    "DT": "data type",
    "Number_Literal": "number literal",
    "Text_Literal": "text literal",
    "Truth_Literal": "truth literal",
}


def expected_text(token_type):
    # 'an identifier', 'a data type' or '}'
    if token_type in TYPE_NAMES:
        name = TYPE_NAMES[token_type]
        return ("an " if name[0] in "aeiou" else "a ") + name
    return f"'{token_type}'"


def found_text(tok):
    if tok.type == "$":
        return "end of input"
    if tok.type in TYPE_NAMES:
        return f"{TYPE_NAMES[tok.type]} '{tok.value}'"
    return f"'{tok.value}'"


class ParseError:
    # kind: missing / unexpected / end_of_input / extra_input / empty
    def __init__(self, kind, message, line, pos):
        self.kind = kind
        self.message = message
        self.line = line
        self.pos = pos

    def __str__(self):
        return f"Syntax Error (line {self.line}): {self.message}"


class Parser:
    # tokens that can start <statement>
    STATEMENT_FIRST = {"declare", "set", "ask", "show", "repeat", "task", "ID"}
    # tokens that end a list of statements ('$' = end of input)
    CLOSERS = ("}", "end", "return", "$")

    def __init__(self, tokens):
        # the end marker '$' is added here, with the line of the last token
        self.tokens = list(tokens)
        last_line = self.tokens[-1].line if self.tokens else 1
        self.tokens.append(Token("$", "$", last_line))
        self.pos = 0          # the counter
        self.errors = []

    #  helpers
    def cur(self):
        return self.tokens[self.pos]

    def peek(self, n=1):
        i = min(self.pos + n, len(self.tokens) - 1)
        return self.tokens[i]

    def check(self, *types):
        return self.cur().type in types

    def match(self, expected):
        # move forward if the current token is the expected one,
        # otherwise record an error and carry on as if it was there
        tok = self.cur()
        if tok.type == expected:
            self.pos += 1
            return tok

        if tok.type == "$":
            self.report("end_of_input",
                        f"Unexpected end of input: expected {expected_text(expected)}")
        else:
            self.report("missing",
                        f"Missing token: expected {expected_text(expected)} "
                        f"but found {found_text(tok)}")
        return None

    def report(self, kind, message):
        # only one error per token, so one mistake does not repeat itself
        if self.errors and self.errors[-1].pos == self.pos:
            return
        line = self.cur().line
        # a missing token belongs to the end of the previous line
        if kind == "missing" and self.pos > 0 and self.tokens[self.pos - 1].line < line:
            line = self.tokens[self.pos - 1].line
        self.errors.append(ParseError(kind, message, line, self.pos))

    def unexpected(self, what):
        # used where more than one token was allowed
        tok = self.cur()
        if tok.type == "$":
            self.report("end_of_input", f"Unexpected end of input: expected {what}")
        else:
            self.report("unexpected",
                        f"Unexpected token {found_text(tok)}: expected {what}")

    def skip_junk(self):
        # error recovery: skip tokens until a closer or a statement on a later line
        err_line = self.cur().line
        self.pos += 1
        while not self.check(*self.CLOSERS):
            tok = self.cur()
            if tok.type in self.STATEMENT_FIRST and tok.line > err_line:
                break
            self.pos += 1

    # entry
    def parse(self):
        if self.check("$"):
            self.report("empty", "Program is empty: expected 'begin'")
            return self.errors

        self.start()

        # nothing is allowed after 'end .'
        if not self.check("$"):
            self.report("extra_input",
                        f"Unexpected token {found_text(self.cur())} after 'end .': "
                        f"nothing is allowed after the end of the program")
        return self.errors

    # <start> -> begin { <statements> } end .
    def start(self):
        self.match("begin")
        self.match("{")
        self.statements()
        self.match("}")
        self.match("end")
        self.match(".")

    # <statements> -> <statement> <statements> | null
    def statements(self, stop=None, what="a statement or '}'"):
        while not self.check(*self.CLOSERS):
            if stop and stop():
                break
            if self.cur().type in self.STATEMENT_FIRST:
                self.statement()
            else:
                self.unexpected(what)
                self.skip_junk()

    # <statement> -> ...
    def statement(self):
        t = self.cur().type
        if t == "declare":
            self.match("declare")
            self.match("ID")
            self.match("as")
            self.match("DT")
            self.declaration_tail()
        elif t == "set":
            self.match("set")
            self.match("ID")
            self.set_tail()
        elif t == "ask":
            self.match("ask")
            self.match("ID")
            self.input_tail()
        elif t == "show":
            self.match("show")
            self.show_tail()
        elif t == "repeat":
            self.match("repeat")
            self.match("while")
            self.condition()
            self.match("{")
            # body: <statements> ID <increment_decrement> }
            self.statements(stop=self._at_loop_update,
                            what="a statement or the loop update "
                                 "(an identifier followed by '++' or '--')")
            if not self.check("ID"):
                self.unexpected("a statement or the loop update "
                                "(an identifier followed by '++' or '--')")
            self.match("ID")
            self.increment_decrement()
            self.match("}")
        elif t == "task":
            self.function_definition()
        elif t == "ID":
            self.match("ID")
            self.id_statement_tail()
        else:
            self.unexpected("a statement")

    def _at_loop_update(self):
        # ID ++/-- followed by '}' is the loop update, not a normal statement
        return (self.check("ID") and self.peek(1).type in ("++", "--")
                and self.peek(2).type == "}")

    # <declaration_tail> -> set to <expression> | array of Number_Literal <array_declaration_tail> | null
    def declaration_tail(self):
        if self.check("set") and self.peek(1).type == "to":
            self.match("set")
            self.match("to")
            self.expression()
        elif self.check("array"):
            self.match("array")
            self.match("of")
            self.match("Number_Literal")
            self.array_declaration_tail()

    # <array_declaration_tail> -> set ID to [ <array_elements> ] | null
    def array_declaration_tail(self):
        # 'set ID to [' (not a new 'set ID to <expr>' statement)
        if (self.check("set") and self.peek(1).type == "ID"
                and self.peek(2).type == "to" and self.peek(3).type == "["):
            self.match("set")
            self.match("ID")
            self.match("to")
            self.match("[")
            self.array_elements()
            self.match("]")

    # <set_tail> -> to <set_to_tail> | at Number_Literal to <expression>
    def set_tail(self):
        if self.check("to"):
            self.match("to")
            self.set_to_tail()
        elif self.check("at"):
            self.match("at")
            self.match("Number_Literal")
            self.match("to")
            self.expression()
        else:
            self.unexpected("'to' or 'at' after 'set'")

    # <set_to_tail> -> <expression> | [ <array_elements> ]
    def set_to_tail(self):
        if self.check("["):
            self.match("[")
            self.array_elements()
            self.match("]")
        else:
            self.expression()

    # <input_tail> -> with Text_Literal | null
    def input_tail(self):
        if self.check("with"):
            self.match("with")
            self.match("Text_Literal")

    # <show_tail> -> <expression> <show_expression_tail> | ID at Number_Literal
    def show_tail(self):
        if self.check("ID") and self.peek(1).type == "at":
            self.match("ID")
            self.match("at")
            self.match("Number_Literal")
        else:
            self.expression()
            self.show_expression_tail()

    # <show_expression_tail> -> if <condition> | null
    def show_expression_tail(self):
        if self.check("if"):
            self.match("if")
            self.condition()

    # <id_statement_tail> -> ++ | -- | ( <arguments> )
    def id_statement_tail(self):
        if self.check("++"):
            self.match("++")
        elif self.check("--"):
            self.match("--")
        elif self.check("("):
            self.match("(")
            self.arguments()
            self.match(")")
        else:
            self.unexpected("'++', '--' or '(' after an identifier")

    # <increment_decrement> -> ++ | --
    def increment_decrement(self):
        if self.check("++"):
            self.match("++")
        elif self.check("--"):
            self.match("--")
        else:
            self.unexpected("'++' or '--'")

    # <condition> is treated as an <expression>
    def condition(self):
        self.expression()

    #  expressions
    # <expression> -> <assignment_expr>
    def expression(self):
        self.assignment_expr()

    # <assignment_expr> -> ID = <assignment_expr> | <logical_or_expr>
    def assignment_expr(self):
        if self.check("ID") and self.peek(1).type == "=":
            self.match("ID")
            self.match("=")
            self.assignment_expr()
        else:
            self.logical_or_expr()

    # <logical_or_expr> -> <logical_and_expr> <logical_or_tail>
    def logical_or_expr(self):
        self.logical_and_expr()
        self.logical_or_tail()

    # <logical_or_tail> -> || <logical_and_expr> <logical_or_tail> | null
    def logical_or_tail(self):
        if self.check("||"):
            self.match("||")
            self.logical_and_expr()
            self.logical_or_tail()

    # <logical_and_expr> -> <logical_not_expr> <logical_and_tail>
    def logical_and_expr(self):
        self.logical_not_expr()
        self.logical_and_tail()

    # <logical_and_tail> -> && <logical_not_expr> <logical_and_tail> | null
    def logical_and_tail(self):
        if self.check("&&"):
            self.match("&&")
            self.logical_not_expr()
            self.logical_and_tail()

    # <logical_not_expr> -> ! <logical_not_expr> | <relational_expr>
    def logical_not_expr(self):
        if self.check("!"):
            self.match("!")
            self.logical_not_expr()
        else:
            self.relational_expr()

    # <relational_expr> -> <additive_expr> <relational_tail>
    def relational_expr(self):
        self.additive_expr()
        self.relational_tail()

    # <relational_tail> -> <relational_operator> <additive_expr> | null
    def relational_tail(self):
        if self.check("<", ">"):
            self.relational_operator()
            self.additive_expr()

    # <relational_operator> -> < <relational_operator_tail> | > <relational_operator_tail>
    def relational_operator(self):
        if self.check("<"):
            self.match("<")
        else:
            self.match(">")
        self.relational_operator_tail()

    # <relational_operator_tail> -> = | null
    def relational_operator_tail(self):
        if self.check("="):
            self.match("=")

    # <additive_expr> -> <multiplicative_expr> <additive_tail>
    def additive_expr(self):
        self.multiplicative_expr()
        self.additive_tail()

    # <additive_tail> -> + <mult> <additive_tail> | - <mult> <additive_tail> | null
    def additive_tail(self):
        if self.check("+", "-"):
            self.match(self.cur().type)
            self.multiplicative_expr()
            self.additive_tail()

    # <multiplicative_expr> -> <postfix_expr> <multiplicative_tail>
    def multiplicative_expr(self):
        self.postfix_expr()
        self.multiplicative_tail()

    # <multiplicative_tail> -> * <postfix> <tail> | / ... | % ... | null
    def multiplicative_tail(self):
        if self.check("*", "/", "%"):
            self.match(self.cur().type)
            self.postfix_expr()
            self.multiplicative_tail()

    # <postfix_expr> -> <primary_expr> <postfix_tail>
    def postfix_expr(self):
        self.primary_expr()
        self.postfix_tail()

    # <postfix_tail> -> ++ | -- | null
    def postfix_tail(self):
        if self.check("++", "--"):
            self.match(self.cur().type)

    # <primary_expr> -> ID | Number_Literal | Text_Literal | Truth_Literal | ( <expression> )
    def primary_expr(self):
        if self.check("ID", "Number_Literal", "Text_Literal", "Truth_Literal"):
            self.match(self.cur().type)
        elif self.check("("):
            self.match("(")
            self.expression()
            self.match(")")
        else:
            self.unexpected("an expression")

    #  arrays
    # <array_elements> -> <value> <array_elements_tail>
    def array_elements(self):
        self.value()
        self.array_elements_tail()

    # <array_elements_tail> -> , <array_elements> | null
    def array_elements_tail(self):
        if self.check(","):
            self.match(",")
            self.array_elements()

    # <value> -> Number_Literal | Text_Literal | Truth_Literal | ID
    def value(self):
        if self.check("Number_Literal", "Text_Literal", "Truth_Literal", "ID"):
            self.match(self.cur().type)
        else:
            self.unexpected("a value (number, text, truth or identifier)")

    #  functions
    # <function_definition> -> task ID ( <parameters> ) { <statements> return <expression> }
    def function_definition(self):
        self.match("task")
        self.match("ID")
        self.match("(")
        self.parameters()
        self.match(")")
        self.match("{")
        self.statements(what="a statement or 'return'")
        self.match("return")
        self.expression()
        self.match("}")

    # <parameters> -> ID <parameters_tail> | null
    def parameters(self):
        if self.check("ID"):
            self.match("ID")
            self.parameters_tail()

    # <parameters_tail> -> , <parameters> | null
    def parameters_tail(self):
        if self.check(","):
            self.match(",")
            self.parameters()

    # <arguments> -> <expression> <arguments_tail> | null
    def arguments(self):
        if not self.check(")"):
            self.expression()
            self.arguments_tail()

    # <arguments_tail> -> , <arguments> | null
    def arguments_tail(self):
        if self.check(","):
            self.match(",")
            self.arguments()