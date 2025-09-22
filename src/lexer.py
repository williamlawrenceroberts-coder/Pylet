import re

# Language definitions
keywords = {
    'let', 'mut', 'const', 'fn', 'return', 'if', 'else', 'while', 'for',
    'break', 'continue', 'true', 'false', 'null', 'match', 'case'
}

functions = {
    'print', 'input', 'to_string', 'to_int', 'to_float', 'abs', 'min', 'max',
    'sqrt', 'pow', 'len', 'push', 'pop', 'assert', 'panic'
}

# Fixed operators - longer operators first to avoid conflicts
operators = [
    '==', '!=', '<=', '>=', '++', '--', '&&', '||',  # Multi-char first
    '+', '-', '*', '/', '%', '=', '<', '>', '!'      # Single-char second
]

separators = r'[\(\)\{\}\[\];,\.]'
whitespace = r'[ \t]+'

# Build regex patterns
token_specification = [
    ('COMMENT',  r'//[^\n]*|/\*.*?\*/'),                       # Comments
    ('NUMBER',   r'[-+]?\d+(\.\d+)?'),                         # Numbers (with sign)
    ('STRING',   r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''),       # Strings
    ('ID',       r'[A-Za-z_]\w*'),                             # Identifiers
    ('OP',       '|'.join(re.escape(op) for op in operators)), # Operators
    ('SEP',      separators),                                  # Separators
    ('NEWLINE',  r'\n'),                                       # Line breaks
    ('WS',       whitespace),                                  # Whitespace
    ('MISMATCH', r'.'),                                        # Any other character
]

# Compile regex with DOTALL so /* */ matches across lines
tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
get_token = re.compile(tok_regex, re.DOTALL).match

def lexer(code):
    pos = 0
    line = 1
    col = 1
    tokens = []
    
    mo = get_token(code, pos)
    while mo is not None:
        kind = mo.lastgroup
        value = mo.group()
        start = pos
        end = mo.end()
        
        if kind == 'NUMBER':
            tokens.append(('NUMBER', value, line, col))
        elif kind == 'ID':
            if value in keywords:
                tokens.append(('KEYWORD', value, line, col))
            elif value in functions:
                tokens.append(('FUNCTION', value, line, col))
            else:
                tokens.append(('IDENT', value, line, col))
        elif kind == 'OP':
            tokens.append(('OP', value, line, col))
        elif kind == 'SEP':
            tokens.append(('SEP', value, line, col))
        elif kind == 'STRING':
            tokens.append(('STRING', value, line, col))
        elif kind == 'COMMENT':
            # Skip comments entirely, but still update position
            pass
        elif kind == 'NEWLINE':
            line += 1
            col = 0  # will get +len(value) below
        elif kind == 'WS':
            # Skip whitespace
            pass
        elif kind == 'MISMATCH':
            raise RuntimeError(f'Unexpected character {value!r} at line {line}, column {col}')
        
        # Update position & column count
        pos = end
        col += len(value)
        mo = get_token(code, pos)
    
    tokens.append(('EOF', '', line, col))
    return tokens
