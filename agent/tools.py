from langchain_core.tools import tool
import ast
from tavily import TavilyClient
import operator as op
import requests
from dotenv import load_dotenv
load_dotenv()
SAFE_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}
def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric constants allowed")
        return node.value
    if isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        operator_fn = SAFE_OPERATORS.get(type(node.op))
        if not operator_fn:
            raise ValueError("Unsupported operator")
        return operator_fn(left, right)
    if isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        operator_fn = SAFE_OPERATORS.get(type(node.op))
        if not operator_fn:
            raise ValueError("Unsupported operator")
        return operator_fn(operand)
    raise ValueError(f"Unsafe expression type: {type(node).__name__}")

@tool
def search_knowledge_base(query:str)->str:
    """Search  the internal knowledge base for relavant information
    Use this FIRST for any questions about the uploaded documents
    Internal data or organisation specific information
    Do NOT use this for recent new or real time information."""
    try:
        response = requests.post(
        "http://localhost:8000/retrieve",
        json={"tenant_id": "default", "query": query, "top_k": 5}
        )
        data = response.json()
        results=data["chunks"]
        if not results:
            return "No relevant documents found for: "+ query
        return "\n".join([r["chunk_text"]for r in results])
    except Exception as e:
        return "No relevant documents found for: "+query





@tool 
def web_search(query:str)->str:
    """Search for the internet for current, real time information.
    Use this for recent events or anything not found in internal documents
    . Use this after searching in the knowledge base first"""
    client=TavilyClient()
    try:
        response=client.search(query=query,max_results=3)
        results=response["results"]
        return "\n".join([r["content"]for r in results])
    except Exception as e:
        return "Web search failed for: "+str(e)



@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.
    Use this for any arithmetic, percentage or numerical calculations.
    Always use this instead of computing in your head."""
    try:
        tree = ast.parse(expression, mode='eval')
        result = safe_eval(tree)
        return str(round(result, 4))
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"