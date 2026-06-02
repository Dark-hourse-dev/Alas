import datetime
from backend.app.llm.tool_registry import register_tool

# --- Tool Schemas ---
GET_TIME_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Get the current time and date.",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The timezone to get the time for (default: local)."
                }
            },
            "required": []
        }
    }
}

CALCULATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Evaluate a mathematical expression safely.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate (e.g., '2 + 2', '100 / 3')."
                }
            },
            "required": ["expression"]
        }
    }
}

# --- Tool Implementations ---

@register_tool("get_current_time", GET_TIME_SCHEMA)
def get_current_time(timezone: str = "local") -> str:
    """Get the current time and date."""
    now = datetime.datetime.now()
    return f"The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}."


@register_tool("calculate", CALCULATE_SCHEMA)
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        # Extremely basic and safe evaluator
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in math expression. Only basic arithmetic is allowed."
        
        # pylint: disable=eval-used
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error calculating expression: {e}"
