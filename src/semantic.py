class SemanticError(Exception):
    """Custom exception for semantic analysis errors"""
    def __init__(self, message, line=None):
        self.message = message
        self.line = line
        super().__init__(self.format_message())

    def format_message(self):
        if self.line:
            return f"Semantic error at line {self.line}: {self.message}"
        return f"Semantic error: {self.message}"


class VariableInfo:
    """Information about a declared variable"""
    def __init__(self, name, var_type, kind, line, is_initialized=False):
        self.name = name
        self.var_type = var_type  # 'int', 'float', 'string', 'bool', 'unknown'
        self.kind = kind  # 'let', 'mut', 'const'
        self.is_initialized = is_initialized
        self.is_mutable = (kind == 'mut')
        self.is_const = (kind == 'const')
        self.is_used = False


class SymbolTable:
    """Scope management for variables"""
    def __init__(self, parent=None, scope_type="block"):
        self.symbols = {}  # name -> VariableInfo
        self.parent = parent
        self.scope_type = scope_type
        self.children = []
        if parent:
            parent.children.append(self)

    def declare(self, name, var_type, kind, line, is_initialized=False):
        if name in self.symbols:
            raise SemanticError(f"Variable '{name}' already declared in this scope", line)
        var_info = VariableInfo(name, var_type, kind, line, is_initialized)
        self.symbols[name] = var_info
        return var_info

    def lookup(self, name):
        """Look up variable recursively in parent scopes"""
        if name in self.symbols:
            self.symbols[name].is_used = True
            return self.symbols[name]
        elif self.parent:
            return self.parent.lookup(name)
        return None

    def get_unused_variables(self):
        return [v for v in self.symbols.values() if not v.is_used and v.name != "_"]


class SemanticAnalyzer:
    """Semantic analyzer enforcing explicit variable declarations"""
    BUILTIN_FUNCTIONS = {
        "print": ("void", []),
        "input": ("string", ["string"]),
        "to_string": ("string", ["any"]),
        "to_int": ("int", ["any"]),
        "to_float": ("float", ["any"]),
        "abs": ("number", ["number"]),
        "min": ("number", ["number", "number"]),
        "max": ("number", ["number", "number"]),
        "sqrt": ("float", ["number"]),
        "pow": ("number", ["number", "number"]),
        "len": ("int", ["string"]),
        "assert": ("void", ["bool"]),
        "panic": ("void", ["string"]),
    }

    def __init__(self):
        self.global_scope = SymbolTable(scope_type="global")
        self.current_scope = self.global_scope
        self.errors = []
        self.warnings = []

    # --- Utility ---
    def error(self, msg, line=None):
        self.errors.append(SemanticError(msg, line))

    def enter_scope(self):
        self.current_scope = SymbolTable(parent=self.current_scope)

    def exit_scope(self):
        unused = self.current_scope.get_unused_variables()
        for var in unused:
            self.warnings.append(f"Warning at line {var.line}: Variable '{var.name}' declared but never used")
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    # --- Analysis ---
    def analyze(self, ast):
        self.visit(ast)
        return len(self.errors) == 0

    def visit(self, node):
        method_name = f"visit_{node.type.lower()}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        self.error(f"Unknown AST node type: {node.type}")

    # --- Node Visitors ---
    def visit_program(self, node):
        for child in node.children:
            self.visit(child)

    def visit_vardecl(self, node):
        kind, name = node.value
        line = getattr(node, "line", None)
        init_type = "unknown"
        if node.children:
            self.visit(node.children[0])
            init_type = self.infer_type(node.children[0])
        try:
            self.current_scope.declare(name, init_type, kind, line, bool(node.children))
        except SemanticError as e:
            self.errors.append(e)

    def visit_assign(self, node):
        name = node.value
        line = getattr(node, "line", None)
        var_info = self.current_scope.lookup(name)
        if not var_info:
            self.error(f"Variable '{name}' not declared", line)
            return
        if not var_info.is_mutable:
            if var_info.is_const:
                self.error(f"Cannot assign to const variable '{name}'", line)
            else:
                self.error(f"Cannot assign to immutable variable '{name}' (declared with 'let')", line)
        if node.children:
            self.visit(node.children[0])
            rhs_type = self.infer_type(node.children[0])
            if var_info.var_type != "unknown" and not self.check_type_compatibility(var_info.var_type, rhs_type):
                self.error(f"Type mismatch: cannot assign {rhs_type} to {var_info.var_type} variable '{name}'", line)
        var_info.is_initialized = True

    def visit_var(self, node):
        name = node.value
        line = getattr(node, "line", None)
        var_info = self.current_scope.lookup(name)
        if not var_info:
            self.error(f"Variable '{name}' not declared", line)
        elif not var_info.is_initialized:
            self.error(f"Variable '{name}' used before initialization", line)

    def visit_binop(self, node):
        for child in node.children:
            self.visit(child)

    def visit_unaryop(self, node):
        for child in node.children:
            self.visit(child)

    def visit_call(self, node):
        func_name = node.value
        line = getattr(node, "line", None)

        # Check built-ins first
        if func_name in self.BUILTIN_FUNCTIONS:
            for arg in node.children:
                self.visit(arg)
            return

        # Then check user-defined functions
        func_info = self.current_scope.lookup(func_name)
        if not func_info or func_info.var_type != 'function':
            self.error(f"Unknown function '{func_name}'", line)

        for arg in node.children:
            self.visit(arg)


    def visit_number(self, node):
        pass

    def visit_string(self, node):
        pass

    def visit_bool(self, node):
        pass

    def visit_function(self, node):
        name, params = node.value
        line = getattr(node, "line", None)

        # 1️⃣ Declare the function first
        try:
            self.current_scope.declare(name, var_type='function', kind='const', line=line)
        except SemanticError as e:
            self.errors.append(e)

        # 2️⃣ Enter a new scope for parameters + function body
        self.enter_scope()
        for param in params:
            self.current_scope.declare(param, var_type='unknown', kind='let', line=line, is_initialized=True)

        for stmt in node.children:
            self.visit(stmt)

        self.exit_scope()



    # --- Type Utilities ---
    def infer_type(self, node):
        if node.type == "Number":
            return "float" if "." in str(node.value) else "int"
        elif node.type == "String":
            return "string"
        elif node.type == "Bool":
            return "bool"
        elif node.type == "Var":
            var_info = self.current_scope.lookup(node.value)
            if var_info:
                return var_info.var_type
            return "unknown"
        elif node.type == "BinOp":
            left = self.infer_type(node.children[0])
            right = self.infer_type(node.children[1])
            op = node.value
            if op == "+" and ("string" in (left, right)):
                return "string"
            if left == "float" or right == "float":
                return "float"
            if left == "int" and right == "int":
                return "int"
            return "unknown"
        elif node.type == "UnaryOp":
            return self.infer_type(node.children[0])
        elif node.type == "Call":
            if node.value in self.BUILTIN_FUNCTIONS:
                return self.BUILTIN_FUNCTIONS[node.value][0]
            return "unknown"
        return "unknown"

    def check_type_compatibility(self, expected, actual):
        if expected == actual:
            return True
        if expected == "float" and actual == "int":
            return True
        if expected == "number" and actual in ("int", "float"):
            return True
        return False

    def print_report(self):
        print("=== Semantic Analysis Report ===")
        for err in self.errors:
            print(f"❌ {err}")
        for w in self.warnings:
            print(f"⚠️ {w}")
        if not self.errors and not self.warnings:
            print("✅ No issues found!")
