# app/workflows.py
from __future__ import annotations

from typing import Any, Dict, List

from .engine import Engine, ToolRegistry, NodeRegistry, NodeDef, GraphDef


# ---------------------- Tools ----------------------


def tool_extract_functions(code: str) -> Dict[str, Any]:
    """
    Very naive function extraction:
    - Treat any line starting with 'def ' as a function definition.
    """
    functions: List[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("def "):
            name_part = stripped[len("def ") :]
            name = name_part.split("(", 1)[0].strip()
            if name:
                functions.append(name)
    return {"functions": functions}


def tool_check_complexity(code: str) -> Dict[str, Any]:
    """Toy complexity metric: combine line count and control-flow keywords."""
    lines = code.splitlines()
    line_count = len(lines)

    control_keywords = [" if ", " for ", " while ", " elif ", " case "]
    control_flow_count = sum(code.count(kw) for kw in control_keywords)

    # Normalize into 0–1
    complexity_score = min(1.0, (line_count / 100.0) + (control_flow_count / 50.0))

    return {
        "lines": line_count,
        "control_flow_count": control_flow_count,
        "complexity_score": complexity_score,
    }


def tool_detect_issues(code: str) -> Dict[str, Any]:
    """
    Rule-based issue detection (purely illustrative).
    """
    issues: List[str] = []

    if "TODO" in code:
        issues.append("Found TODO comments in the code.")
    if "print(" in code:
        issues.append("Debug 'print' statements present.")
    if len(code) > 2000:
        issues.append("File is quite long; consider splitting it.")
    if "import *" in code:
        issues.append("Wildcard imports detected; prefer explicit imports.")

    return {"issues": issues, "issue_count": len(issues)}


def tool_suggest_improvements(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate text suggestions + a toy quality_score.
    quality_score in [0,1]; higher is better.
    """
    suggestions: List[str] = []

    complexity_score = float(summary.get("complexity_score", 0.0))
    issue_count = int(summary.get("issue_count", 0))

    if complexity_score > 0.7:
        suggestions.append("Refactor large or complex functions into smaller units.")
    if issue_count > 0:
        suggestions.append("Address the detected issues before merging.")
    if complexity_score <= 0.3 and issue_count == 0:
        suggestions.append("Code looks clean and simple. Good job!")

    # Toy quality metric
    quality_score = max(
        0.0,
        1.0 - 0.5 * complexity_score - 0.1 * issue_count,
    )

    return {
        "suggestions": suggestions,
        "quality_score": quality_score,
    }


# ---------------------- Nodes ----------------------


def node_extract(state: Dict[str, Any], tools: Dict[str, Any]) -> None:
    code = state.get("code", "")
    result = tools["extract_functions"](code)
    state["functions"] = result["functions"]
    return None  # follow default edge


def node_check_complexity(state: Dict[str, Any], tools: Dict[str, Any]) -> None:
    code = state.get("code", "")
    result = tools["check_complexity"](code)
    state["complexity"] = result
    return None


def node_detect_issues(state: Dict[str, Any], tools: Dict[str, Any]) -> None:
    code = state.get("code", "")
    result = tools["detect_issues"](code)
    state["issues"] = result["issues"]
    state["issue_count"] = result["issue_count"]
    return None


def node_suggest_improvements(state: Dict[str, Any], tools: Dict[str, Any]) -> None:
    complexity_info = state.get("complexity", {}) or {}
    issue_count = int(state.get("issue_count", 0))

    summary_input = {
        "complexity_score": float(complexity_info.get("complexity_score", 0.0)),
        "issue_count": issue_count,
    }
    result = tools["suggest_improvements"](summary_input)

    state["suggestions"] = result["suggestions"]
    state["quality_score"] = result["quality_score"]
    state["iterations"] = int(state.get("iterations", 0)) + 1
    return None


def node_evaluate_quality(state: Dict[str, Any], tools: Dict[str, Any]) -> str | None:
    """
    Branch / loop:
    - If quality_score >= threshold -> stop
    - Else, if iterations < max_loops -> go back to 'suggest_improvements'
    - Else -> stop anyway
    """
    threshold = float(state.get("threshold", 0.8))
    quality = float(state.get("quality_score", 0.0))
    iterations = int(state.get("iterations", 0))
    max_loops = int(state.get("max_loops", 3))

    if quality >= threshold:
        state["status"] = "accepted"
        state["done"] = True
        return None  # end

    if iterations >= max_loops:
        state["status"] = "stopped_max_loops"
        state["done"] = True
        return None  # end

    # Loop back: do more suggestions/refinements
    return "suggest_improvements"


# ---------------------- Registration helper ----------------------


def register_code_review_workflow(
    engine: Engine,
    tools: ToolRegistry,
    nodes: NodeRegistry,
) -> str:
    """
    Register tools + nodes + a fixed graph for the Code Review mini-agent.
    Returns the graph_id.
    """

    # ---- Tools
    tools.register("extract_functions", tool_extract_functions)
    tools.register("check_complexity", tool_check_complexity)
    tools.register("detect_issues", tool_detect_issues)
    tools.register("suggest_improvements", tool_suggest_improvements)

    # ---- Nodes
    nodes.register("extract", node_extract)
    nodes.register("check_complexity", node_check_complexity)
    nodes.register("detect_issues", node_detect_issues)
    nodes.register("suggest_improvements", node_suggest_improvements)
    nodes.register("evaluate_quality", node_evaluate_quality)

    # ---- Graph definition
    graph_id = "code_review"

    node_defs = {
        "extract": NodeDef("extract", node_extract, "Extract functions from source code"),
        "check_complexity": NodeDef(
            "check_complexity", node_check_complexity, "Compute a toy complexity score"
        ),
        "detect_issues": NodeDef(
            "detect_issues", node_detect_issues, "Find basic code issues"
        ),
        "suggest_improvements": NodeDef(
            "suggest_improvements",
            node_suggest_improvements,
            "Suggest improvements and compute a quality score",
        ),
        "evaluate_quality": NodeDef(
            "evaluate_quality",
            node_evaluate_quality,
            "Decide whether to loop or stop based on quality score",
        ),
    }

    edges = {
        "extract": "check_complexity",
        "check_complexity": "detect_issues",
        "detect_issues": "suggest_improvements",
        "suggest_improvements": "evaluate_quality",
        "evaluate_quality": None,  # normally ended here, unless node overrides
    }

    graph = GraphDef(
        id=graph_id,
        name="Code Review Mini-Agent",
        nodes=node_defs,
        edges=edges,
        start_node="extract",
    )
    engine.add_graph(graph)
    return graph_id
