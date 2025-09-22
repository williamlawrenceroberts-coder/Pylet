import math
from parser import ASTNode

class Heap:
    def __init__(self):
        self.memory = {}
        self.ref_count = {}
        self.next_id = 0

    def allocate(self, value):
        obj_id = self.next_id
        self.next_id += 1
        self.memory[obj_id] = value
        self.ref_count[obj_id] = 1
        return obj_id

    def retain(self, obj_id):
        if obj_id is not None and obj_id in self.ref_count:
            self.ref_count[obj_id] += 1

    def release(self, obj_id):
        if obj_id is not None and obj_id in self.ref_count:
            self.ref_count[obj_id] -= 1
            if self.ref_count[obj_id] <= 0:
                del self.memory[obj_id]
                del self.ref_count[obj_id]

    def get(self, obj_id):
        return self.memory[obj_id]

class Interpreter:
    def __init__(self):
        self.heap = Heap()
        self.global_env = {}
        self.env_stack = [self.global_env]

        self.builtins = {
            "print": self._builtin_print,
            "input": self._builtin_input,
            "to_int": lambda args: self.heap.allocate(int(args[0])),
            "to_float": lambda args: self.heap.allocate(float(args[0])),
            "to_string": lambda args: self.heap.allocate(str(args[0])),
            "abs": lambda args: self.heap.allocate(abs(args[0])),
            "min": lambda args: self.heap.allocate(min(args)),
            "max": lambda args: self.heap.allocate(max(args)),
            "sqrt": lambda args: self.heap.allocate(math.sqrt(args[0])),
            "pow": lambda args: self.heap.allocate(args[0] ** args[1]),
            "len": lambda args: self.heap.allocate(len(args[0])),
            "assert": self._builtin_assert,
            "panic": self._builtin_panic,
        }

    # --- Builtins ---
    def _builtin_print(self, args):
        print(*args)
        return None

    def _builtin_input(self, args):
        prompt = args[0] if args else ""
        val = input(str(prompt))
        return self.heap.allocate(val)

    def _builtin_assert(self, args):
        if not args[0]:
            raise RuntimeError("Assertion failed")
        return None

    def _builtin_panic(self, args):
        raise RuntimeError(args[0])

    # --- Environment helpers ---
    def push_env(self):
        self.env_stack.append({})
        return self.env_stack[-1]

    def pop_env(self):
        local_env = self.env_stack.pop()
        for obj_id in local_env.values():
            self.heap.release(obj_id)

    def current_env(self):
        return self.env_stack[-1]

    def lookup(self, name):
        for env in reversed(self.env_stack):
            if name in env:
                return env[name]
        raise RuntimeError(f"Variable '{name}' not defined")

    def assign(self, name, obj_id):
        for env in reversed(self.env_stack):
            if name in env:
                old_id = env[name]
                self.heap.release(old_id)
                env[name] = obj_id
                self.heap.retain(obj_id)
                return
        # Not found: assign in current env
        self.current_env()[name] = obj_id
        self.heap.retain(obj_id)

    # --- Evaluation ---
    def eval(self, node):
        t = node.type

        if t == "Program":
            result = None
            for child in node.children:
                result = self.eval(child)
            return result

        elif t == "VarDecl":
            kind, name = node.value
            val_id = self.eval(node.children[0]) if node.children else None
            if val_id is not None:
                self.heap.retain(val_id)
            self.current_env()[name] = val_id
            return val_id

        elif t == "Assign":
            name = node.value
            val_id = self.eval(node.children[0])
            self.assign(name, val_id)
            return val_id

        elif t == "Var":
            return self.lookup(node.value)

        elif t == "Number":
            return self.heap.allocate(float(node.value) if "." in str(node.value) else int(node.value))

        elif t == "String":
            val = str(node.value)
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            return self.heap.allocate(val)

        elif t == "Bool":
            return self.heap.allocate(bool(node.value))

        elif t == "Null":
            return self.heap.allocate(None)

        elif t == "BinOp":
            left = self.heap.get(self.eval(node.children[0]))
            right = self.heap.get(self.eval(node.children[1]))
            op = node.value

            if op == "+": res = left + right
            elif op == "-": res = left - right
            elif op == "*": res = left * right
            elif op == "/": res = left / right
            elif op == "%": res = left % right
            elif op == "==": res = left == right
            elif op == "!=": res = left != right
            elif op == "<": res = left < right
            elif op == ">": res = left > right
            elif op == "<=": res = left <= right
            elif op == ">=": res = left >= right
            elif op == "&&": res = bool(left) and bool(right)
            elif op == "||": res = bool(left) or bool(right)
            else: raise RuntimeError(f"Unknown operator {op}")
            return self.heap.allocate(res)

        elif t == "UnaryOp":
            operand = self.heap.get(self.eval(node.children[0]))
            op = node.value
            if op == "+": res = +operand
            elif op == "-": res = -operand
            elif op == "!": res = not operand
            elif op == "++": res = operand + 1
            elif op == "--": res = operand - 1
            else: raise RuntimeError(f"Unknown unary operator {op}")
            return self.heap.allocate(res)

        elif t == "Function":
            name, params = node.value
            self.current_env()[name] = node  # store AST node
            return None

        elif t == "Return":
            val_id = self.eval(node.children[0])
            raise ReturnValue(self.heap.get(val_id))

        elif t == "Call":
            func_name = node.value
            args = [self.heap.get(self.eval(arg)) for arg in node.children]

            # Built-in function
            if func_name in self.builtins:
                return self.builtins[func_name](args)

            # User-defined function
            func_node = self.lookup(func_name)
            if not isinstance(func_node, ASTNode) or func_node.type != "Function":
                raise RuntimeError(f"'{func_name}' is not a function")

            _, param_names = func_node.value
            if len(param_names) != len(args):
                raise RuntimeError(f"{func_name} expects {len(param_names)} args, got {len(args)}")

            # Create local environment for function call
            self.push_env()
            local_env = self.current_env()
            for pname, val in zip(param_names, args):
                local_env[pname] = self.heap.allocate(val)

            try:
                result = None
                for stmt in func_node.children:
                    result = self.eval(stmt)
                self.pop_env()
                return result
            except ReturnValue as ret:
                self.pop_env()
                return self.heap.allocate(ret.value)

        else:
            raise RuntimeError(f"Unknown node type: {t}")


class ReturnValue(Exception):
    """Used internally to handle return statements."""
    def __init__(self, value):
        self.value = value
