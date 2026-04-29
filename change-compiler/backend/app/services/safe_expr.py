import ast
import operator
from dataclasses import dataclass


class UnsafeExpressionError(ValueError):
    pass


_CMP_OPS: dict[type[ast.cmpop], object] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


_BOOL_OPS: dict[type[ast.boolop], object] = {
    ast.And: all,
    ast.Or: any,
}


_UNARY_OPS: dict[type[ast.unaryop], object] = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


@dataclass(frozen=True)
class CompiledExpr:
    expr: str
    tree: ast.Expression


def compile_expr(expr: str) -> CompiledExpr:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError("Invalid expression syntax") from exc

    _validate(tree)
    return CompiledExpr(expr=expr, tree=tree)


def eval_expr(compiled: CompiledExpr, context: dict[str, object]) -> object:
    return _eval_node(compiled.tree.body, context)


def eval_bool(expr: str, context: dict[str, object]) -> bool:
    compiled = compile_expr(expr)
    return bool(eval_expr(compiled, context))


def _validate(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            raise UnsafeExpressionError("Function calls are not allowed")
        if isinstance(node, ast.Attribute):
            raise UnsafeExpressionError("Attribute access is not allowed")
        if isinstance(node, ast.Subscript):
            raise UnsafeExpressionError("Subscript access is not allowed")
        if isinstance(node, ast.Lambda):
            raise UnsafeExpressionError("Lambda is not allowed")
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            raise UnsafeExpressionError("Import is not allowed")
        if isinstance(node, ast.Name):
            # Names are allowed but must resolve in context at runtime.
            continue
        if isinstance(node, (ast.Expression, ast.Load, ast.Constant)):
            continue
        if isinstance(node, (ast.BoolOp, ast.UnaryOp, ast.BinOp, ast.Compare)):
            continue
        if isinstance(node, (ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd)):
            continue
        if isinstance(node, tuple(_CMP_OPS.keys())):
            continue
        if isinstance(node, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
            continue

        raise UnsafeExpressionError(f"Unsupported syntax: {type(node).__name__}")


def _eval_node(node: ast.AST, context: dict[str, object]) -> object:
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in context:
            raise UnsafeExpressionError(f"Unknown variable: {node.id}")
        return context[node.id]

    if isinstance(node, ast.BoolOp):
        op_type = type(node.op)
        if op_type not in _BOOL_OPS:
            raise UnsafeExpressionError("Unsupported boolean operator")
        values = [_eval_node(v, context) for v in node.values]
        fn = _BOOL_OPS[op_type]
        return fn(bool(v) for v in values)  # type: ignore[arg-type]

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise UnsafeExpressionError("Unsupported unary operator")
        val = _eval_node(node.operand, context)
        return _UNARY_OPS[op_type](val)  # type: ignore[operator]

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        if isinstance(node.op, ast.Add):
            return left + right  # type: ignore[operator]
        if isinstance(node.op, ast.Sub):
            return left - right  # type: ignore[operator]
        if isinstance(node.op, ast.Mult):
            return left * right  # type: ignore[operator]
        if isinstance(node.op, ast.Div):
            return left / right  # type: ignore[operator]
        if isinstance(node.op, ast.Mod):
            return left % right  # type: ignore[operator]
        raise UnsafeExpressionError("Unsupported binary operator")

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            right = _eval_node(comparator, context)
            op_type = type(op)
            if op_type not in _CMP_OPS:
                raise UnsafeExpressionError("Unsupported comparison operator")
            if not _CMP_OPS[op_type](left, right):  # type: ignore[operator]
                return False
            left = right
        return True

    raise UnsafeExpressionError(f"Unsupported node: {type(node).__name__}")

