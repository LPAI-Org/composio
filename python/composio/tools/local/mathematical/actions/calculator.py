import ast
import operator
from typing import Dict, Union, Any

from pydantic import BaseModel, Field
from composio.tools.base.local import LocalAction

class CalculatorRequest(BaseModel):
    operation: str = Field(
        ...,
        description="A mathematical expression, examples: 200*7 or 5000/2*10",
        json_schema_extra={"file_readable": True},
    )

class CalculatorResponse(BaseModel):
    result: str = Field(..., description="Result of the calculation")

class Calculator(LocalAction[CalculatorRequest, CalculatorResponse]):
    """
    Performs mathematical calculations such as addition, subtraction, multiplication, and division.
    """

    _tags = ["calculator"]

    # Define supported operators
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def execute(self, request: CalculatorRequest, metadata: Dict) -> CalculatorResponse:
        """
        Executes the calculator operation with proper error handling.
        """
        try:
            node = ast.parse(request.operation, mode="eval").body
            result = self._safe_eval(node)
            return CalculatorResponse(result=str(result))
        except SyntaxError:
            return CalculatorResponse(result="Error: Invalid mathematical expression")
        except (TypeError, ValueError) as e:
            return CalculatorResponse(result=f"Error: {str(e)}")
        except Exception as e:
            return CalculatorResponse(result="Error: An unexpected error occurred while calculating")

    def _safe_eval(self, node: ast.AST) -> Union[int, float]:
        """
        Main evaluation method that dispatches to specific node handlers.
        """
        handlers: Dict[type[ast.AST], Any] = {
            ast.Constant: self._eval_constant,
            ast.BinOp: self._eval_binary_operation,
            ast.UnaryOp: self._eval_unary_operation
        }

        handler = handlers.get(type(node))
        if handler:
            return handler(node)
        raise TypeError(f"Unsupported type: {type(node).__name__}")

    def _eval_constant(self, node: ast.Constant) -> Union[int, float]:
        """
        Evaluates constant nodes (numbers).
        """
        if isinstance(node.value, (int, float)):
            return node.value
        raise TypeError(f"Unsupported constant type: {type(node.value).__name__}")

    def _eval_binary_operation(self, node: ast.BinOp) -> Union[int, float]:
        """
        Evaluates binary operations (e.g., addition, multiplication).
        """
        left = self._safe_eval(node.left)
        right = self._safe_eval(node.right)
        op_type = type(node.op)

        if op_type not in self.operators:
            raise TypeError(f"Unsupported binary operator: {op_type.__name__}")

        # Check for division by zero before operation
        if op_type == ast.Div and right == 0:
            raise ValueError("Division by zero is not allowed")

        return self.operators[op_type](left, right)

    def _eval_unary_operation(self, node: ast.UnaryOp) -> Union[int, float]:
        """
        Evaluates unary operations (e.g., negation).
        """
        operand = self._safe_eval(node.operand)
        op_type = type(node.op)

        if op_type not in self.operators:
            raise TypeError(f"Unsupported unary operator: {op_type.__name__}")

        return self.operators[op_type](operand)