import sys
from lexer import lexer  # your lexer.py
from parser import Parser  # your parser.py
from semantic import SemanticAnalyzer  # your new semantic.py
from interpreter import Interpreter  # your interpreter.py

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <source_file>")
        sys.exit(1)

    source_file = sys.argv[1]

    # Read source code
    try:
        with open(source_file, "r") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{source_file}' not found.")
        sys.exit(1)

    # Lexical analysis
    try:
        tokens = lexer(code)
    except Exception as e:
        print(f"Lexical error: {e}")
        sys.exit(1)

    # Parsing
    try:
        parser = Parser(tokens)
        ast = parser.parse()
    except Exception as e:
        print(f"Parsing error: {e}")
        sys.exit(1)

    # Semantic analysis
    analyzer = SemanticAnalyzer()
    try:
        analyzer.analyze(ast)
    except Exception as e:
        print(f"Semantic analysis failed: {e}")
        sys.exit(1)
    if analyzer.errors:
        for err in analyzer.errors:
            print(f"{err}")
        sys.exit(1)
    else:


        interpreter = Interpreter()
        try:
            interpreter.eval(ast)
        except Exception as e:
            print(f"Runtime error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
