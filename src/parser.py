class ASTNode:
    def __init__(self, type_, value=None, children=None):
        self.type = type_
        self.value = value
        self.children = children or []

    def __repr__(self):
        return f"ASTNode({self.type!r}, {self.value!r}, {self.children!r})"


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        if self.pos >= len(self.tokens):
            return ('EOF', '', 0, 0)
        return self.tokens[self.pos]

    def peek(self, offset=1):
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return ('EOF', '', 0, 0)
        return self.tokens[pos]

    def at_end(self):
        return self.pos >= len(self.tokens) or self.current()[0] == 'EOF'

    def eat(self, type_=None, value=None):
        if self.at_end():
            raise SyntaxError("Unexpected end of input")
        tok = self.current()
        if type_ and tok[0] != type_:
            raise SyntaxError(f"Expected {type_}, got {tok[0]} '{tok[1]}' at line {tok[2]}")
        if value and tok[1] != value:
            raise SyntaxError(f"Expected '{value}', got '{tok[1]}' at line {tok[2]}")
        self.pos += 1
        return tok

    def parse(self):
        nodes = []
        while not self.at_end():
            nodes.append(self.statement())
        return ASTNode('Program', children=nodes)

    # --- Statements ---
    def statement(self):
        tok = self.current()

        if tok[0] == 'KEYWORD':
            if tok[1] in ('let', 'mut', 'const'):
                return self.var_decl()
            elif tok[1] == 'fn':
                return self.function_def()
            elif tok[1] == 'return':
                return self.return_stmt()
        elif tok[0] in ('IDENT', 'FUNCTION'):
            if self.peek()[1] == '(':
                # function call
                name = self.eat()[1]
                args = self.arguments()
                self.eat('SEP', ';')
                return ASTNode('Call', value=name, children=args)
            elif self.peek()[1] == '=':
                return self.assignment()
        raise SyntaxError(f"Unexpected token {tok[0]} '{tok[1]}' at line {tok[2]}")

    def var_decl(self):
        kind = self.eat('KEYWORD')[1]
        name = self.eat('IDENT')[1]
        self.eat('OP', '=')
        expr = self.expression()
        self.eat('SEP', ';')
        return ASTNode('VarDecl', value=(kind, name), children=[expr])

    def assignment(self):
        name = self.eat('IDENT')[1]
        self.eat('OP', '=')
        expr = self.expression()
        self.eat('SEP', ';')
        return ASTNode('Assign', value=name, children=[expr])

    def function_def(self):
        self.eat('KEYWORD', 'fn')
        name = self.eat('IDENT')[1]

        # parameters
        self.eat('SEP', '(')
        params = []
        if self.current()[1] != ')':
            params.append(self.eat('IDENT')[1])
            while self.current()[1] == ',':
                self.eat('SEP', ',')
                params.append(self.eat('IDENT')[1])
        self.eat('SEP', ')')

        # body
        self.eat('SEP', '{')
        body = []
        while self.current()[1] != '}':
            body.append(self.statement())
        self.eat('SEP', '}')

        return ASTNode('Function', value=(name, params), children=body)

    def return_stmt(self):
        self.eat('KEYWORD', 'return')
        expr = self.expression()
        self.eat('SEP', ';')
        return ASTNode('Return', children=[expr])

    # --- Expressions ---
    def arguments(self):
        args = []
        self.eat('SEP', '(')
        if self.current()[1] != ')':
            args.append(self.expression())
            while self.current()[1] == ',':
                self.eat('SEP', ',')
                args.append(self.expression())
        self.eat('SEP', ')')
        return args

    def expression(self):
        return self.parse_binary_expr()

    def parse_binary_expr(self, min_prec=0):
        left = self.parse_primary()
        while True:
            tok = self.current()
            if tok[0] == 'OP' and tok[1] in ('+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=', '&&', '||'):
                prec = self.get_precedence(tok[1])
                if prec < min_prec:
                    break
                op = self.eat('OP')[1]
                right = self.parse_binary_expr(prec + 1)
                left = ASTNode('BinOp', value=op, children=[left, right])
            else:
                break
        return left

    def parse_primary(self):
        tok = self.current()
        if tok[0] == 'NUMBER':
            return ASTNode('Number', value=self.eat('NUMBER')[1])
        elif tok[0] == 'STRING':
            return ASTNode('String', value=self.eat('STRING')[1])
        elif tok[0] == 'KEYWORD' and tok[1] in ('true', 'false'):
            return ASTNode('Bool', value=(self.eat('KEYWORD')[1] == 'true'))
        elif tok[0] == 'KEYWORD' and tok[1] == 'null':
            self.eat('KEYWORD')
            return ASTNode('Null')
        elif tok[0] in ('IDENT', 'FUNCTION'):
            name = self.eat()[1]
            if self.current()[1] == '(':
                args = self.arguments()
                return ASTNode('Call', value=name, children=args)
            return ASTNode('Var', value=name)
        elif tok[0] == 'SEP' and tok[1] == '(':
            self.eat('SEP', '(')
            expr = self.expression()
            self.eat('SEP', ')')
            return expr
        elif tok[0] == 'OP' and tok[1] in ('+', '-', '!', '++', '--'):
            op = self.eat('OP')[1]
            operand = self.parse_primary()
            return ASTNode('UnaryOp', value=op, children=[operand])
        else:
            raise SyntaxError(f"Unexpected token {tok[0]} '{tok[1]}' at line {tok[2]} in expression")

    def get_precedence(self, op):
        precedences = {
            '||': 1, '&&': 2,
            '==': 3, '!=': 3, '<': 4, '>': 4, '<=': 4, '>=': 4,
            '+': 5, '-': 5,
            '*': 6, '/': 6, '%': 6,
        }
        return precedences.get(op, 0)
