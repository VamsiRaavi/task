# app/main.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .engine import (
    Engine,
    ToolRegistry,
    NodeRegistry,
    GraphDef,
    NodeDef,
)
from .workflows import register_code_review_workflow


# ---------------- Global engine & registries ----------------

tool_registry = ToolRegistry()
node_registry = NodeRegistry()
engine = Engine(tools=tool_registry, nodes=node_registry)

# Register built-in example workflow
CODE_REVIEW_GRAPH_ID = register_code_review_workflow(
    engine=engine, tools=tool_registry, nodes=node_registry
)


# ---------------- Pydantic schemas ----------------

class GraphCreateNode(BaseModel):
    name: str = Field(..., description="Node name inside this graph")
    function: str = Field(..., description="Name of registered node function")


class GraphCreateRequest(BaseModel):
    name: str
    nodes: List[GraphCreateNode]
    edges: Dict[str, Optional[str]]
    start_node: str


class GraphCreateResponse(BaseModel):
    graph_id: str


class GraphRunRequest(BaseModel):
    graph_id: str = Field(..., description="ID of an existing graph")
    initial_state: Dict[str, Any] = Field(default_factory=dict)


class GraphRunResponse(BaseModel):
    run_id: str
    final_state: Dict[str, Any]
    log: List[Dict[str, Any]]


class RunStateResponse(BaseModel):
    run_id: str
    graph_id: str
    state: Dict[str, Any]
    current_node: Optional[str]
    finished: bool
    log: List[Dict[str, Any]]


# ---------------- FastAPI app ----------------

app = FastAPI(
    title="Mini Agent Workflow Engine",
    description="A very small LangGraph-like engine with nodes, state, edges, branching, and loops.",
    version="0.1.0",
)


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "Mini agent workflow engine is running.",
        
    }


# --------- POST /graph/create ---------


@app.post("/graph/create", response_model=GraphCreateResponse)
def create_graph(payload: GraphCreateRequest) -> GraphCreateResponse:
    """
    Create a new graph from a JSON spec.

    - Nodes must reference node functions that are already registered in NodeRegistry.
    - Edges map node_name -> next_node_name (or null to stop).
    """
    # Map node_name -> function_name
    node_specs: Dict[str, str] = {n.name: n.function for n in payload.nodes}

    # Validate that all edges refer to known nodes (if not null)
    for from_node, to_node in payload.edges.items():
        if from_node not in node_specs:
            raise HTTPException(
                status_code=400,
                detail=f"Edge source node '{from_node}' not in nodes list.",
            )
        if to_node is not None and to_node not in node_specs:
            raise HTTPException(
                status_code=400,
                detail=f"Edge target node '{to_node}' not in nodes list.",
            )

    try:
        graph = engine.create_graph_from_spec(
            name=payload.name,
            node_specs=node_specs,
            edges=payload.edges,
            start_node=payload.start_node,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown node function: {e}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    return GraphCreateResponse(graph_id=graph.id)


# --------- POST /graph/run ---------


@app.post("/graph/run", response_model=GraphRunResponse)
def run_graph(payload: GraphRunRequest) -> GraphRunResponse:
    """
    Run an existing graph end-to-end (synchronously) with an initial state.
    """
    try:
        run_record = engine.run_graph(
            graph_id=payload.graph_id,
            initial_state=payload.initial_state,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Graph not found")

    return GraphRunResponse(
        run_id=run_record.id,
        final_state=run_record.state,
        log=run_record.log,
    )


# --------- GET /graph/state/{run_id} ---------


@app.get("/graph/state/{run_id}", response_model=RunStateResponse)
def get_run_state(run_id: str) -> RunStateResponse:
    """
    Get the state and log of a workflow run.
    In this basic version, runs are synchronous, so this returns final state.
    """
    try:
        run_record = engine.get_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStateResponse(
        run_id=run_record.id,
        graph_id=run_record.graph_id,
        state=run_record.state,
        current_node=run_record.current_node,
        finished=run_record.finished,
        log=run_record.log,
    )
