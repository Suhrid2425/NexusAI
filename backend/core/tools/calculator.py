
import ast
import math
import operator


# Supported arithmetic operators
BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Supported unary operators
UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Supported mathematical functions
MATH_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "fabs": math.fabs,
}

# Allowed mathematical constants
MATH_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


MAX_EXPRESSION_LENGTH = 200
MAX_POWER = 1000
MAX_RESULT_MAGNITUDE = 10**100


class CalculatorError(ValueError):
    """Raised when a calculation is invalid or unsupported."""


def _evaluate_node(node):
    """Safely evaluate an approved mathematical AST node."""

    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)

    # Numbers
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise CalculatorError("Boolean values are not allowed.")

        if isinstance(node.value, (int, float)):
            return node.value

        raise CalculatorError("Only numeric values are allowed.")

    # Mathematical constants
    if isinstance(node, ast.Name):
        if node.id in MATH_CONSTANTS:
            return MATH_CONSTANTS[node.id]

        raise CalculatorError(f"Unsupported constant: {node.id}")

    # Binary operations: +, -, *, /, etc.
    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)

        if operator_type not in BINARY_OPERATORS:
            raise CalculatorError("Unsupported arithmetic operator.")

        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)

        if operator_type is ast.Pow:
            if abs(right) > MAX_POWER:
                raise CalculatorError("Exponent is too large.")

            if abs(left) > 10**10:
                raise CalculatorError("Base is too large.")

        if operator_type is ast.Mult:
            if abs(left) > 10**50 or abs(right) > 10**50:
                raise CalculatorError("Multiplication operands are too large.")

        if operator_type in (ast.Div, ast.FloorDiv, ast.Mod):
            if right == 0:
                raise CalculatorError("Division by zero is not allowed.")

        return BINARY_OPERATORS[operator_type](left, right)

    # Unary operations: +x, -x
    if isinstance(node, ast.UnaryOp):
        operator_type = type(node.op)

        if operator_type not in UNARY_OPERATORS:
            raise CalculatorError("Unsupported unary operator.")

        return UNARY_OPERATORS[operator_type](
            _evaluate_node(node.operand)
        )

    # Mathematical functions
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise CalculatorError("Unsupported function call.")

        function_name = node.func.id

        if function_name not in MATH_FUNCTIONS:
            raise CalculatorError(
                f"Unsupported mathematical function: {function_name}"
            )

        if node.keywords:
            raise CalculatorError("Keyword arguments are not allowed.")

        if len(node.args) != 1:
            raise CalculatorError(
                f"{function_name} requires exactly one argument."
            )

        argument = _evaluate_node(node.args[0])

        if function_name == "factorial":
            if not isinstance(argument, int) or argument < 0:
                raise CalculatorError(
                    "Factorial requires a non-negative integer."
                )

            if argument > 1000:
                raise CalculatorError("Factorial input is too large.")

        return MATH_FUNCTIONS[function_name](argument)

    raise CalculatorError(
        f"Unsupported expression element: {type(node).__name__}"
    )


def calculate(expression):
    """
    Safely calculate a mathematical expression.

    Never uses eval() or exec().
    """

    if not isinstance(expression, str):
        raise CalculatorError("Expression must be text.")

    expression = expression.strip()

    if not expression:
        raise CalculatorError("Expression cannot be empty.")

    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise CalculatorError("Expression is too long.")

    try:
        syntax_tree = ast.parse(expression, mode="eval")
        result = _evaluate_node(syntax_tree)

    except CalculatorError:
        raise

    except ZeroDivisionError:
        raise CalculatorError("Division by zero is not allowed.")

    except (ValueError, OverflowError):
        raise CalculatorError(
            "Invalid mathematical expression or domain."
        )

    except SyntaxError:
        raise CalculatorError("Invalid mathematical expression.")

    except Exception as exc:
        raise CalculatorError("Calculation could not be completed.") from exc

    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise CalculatorError("Calculation did not produce a numeric result.")

    if not math.isfinite(result):
        raise CalculatorError("Result is not finite.")

    if abs(result) > MAX_RESULT_MAGNITUDE:
        raise CalculatorError("Result is too large.")

    return result
