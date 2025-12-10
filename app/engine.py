# app/engine.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

State = Dict[str, Any]
ToolFn = Callable[..., Any]
NodeFn = Callable[[State, Dict[str, ToolFn]], Optional[str]]  # returns optional next node name override


class ToolRegistry:
    """Simple registry of tools that nodes can call."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, func: ToolFn) -> None:
        self._tools[name] = func

    def get(self, name: str) -> ToolFn:
        return self._tools[name]

    def all(self) -> Dict[str, ToolFn]:
        return self._tools


class NodeRegistry:
    """Optional registry of reusable node functions (by name)."""

    def __init__(self) -> None:
        self._nodes: Dict[str, NodeFn] = {}

    def register(self, name: str, func: NodeFn) -> None:
        self._nodes[name] = func

    def get(self, name: str) -> NodeFn:
        return self._nodes[name]

    def all(self) -> Dict[str, NodeFn]:
        return self._nodes


@dataclass
class NodeDef:
    name: str
    func: NodeFn
    description: str = ""


@dataclass
class GraphDef:
    id: str
    name: str
    nodes: Dict[str, NodeDef]
    edges: Dict[str, Optional[str]]  # node_name -> next_node_name (or None to stop)
    start_node: str


@dataclass
class RunRecord:
    id: str
    graph_id: str
    state: State
    current_node: Optional[str]
    log: List[Dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


class Engine:
    """
    Minimal workflow engine:
    - Maintains graphs (nodes + edges)
    - Runs them synchronously
    - Stores run history + state
    - Supports branching/looping via:
      * static edges
      * optional next-node override returned by NodeFn
    """

    def __init__(self, tools: ToolRegistry, nodes: NodeRegistry) -> None:
        self.tools_registry = tools
        self.node_registry = nodes
        self.graphs: Dict[str, GraphDef] = {}
        self.runs: Dict[str, RunRecord] = {}

    # ---------------- Graph management ----------------

    def add_graph(self, graph: GraphDef) -> None:
        self.graphs[graph.id] = graph

    def create_graph_from_spec(
        self,
        name: str,
        node_specs: Dict[str, str],
        edges: Dict[str, Optional[str]],
        start_node: str,
    ) -> GraphDef:
        """
        Create a graph from a JSON spec:
        node_specs: { "node_name": "node_function_name" }
        Edges: { "node_name": "next_node_name_or_null" }
        """
        graph_id = str(uuid.uuid4())
        nodes: Dict[str, NodeDef] = {}

        for node_name, fn_name in node_specs.items():
            fn = self.node_registry.get(fn_name)  # raises KeyError if not found
            nodes[node_name] = NodeDef(name=node_name, func=fn)

        if start_node not in nodes:
            raise ValueError(f"start_node '{start_node}' not in nodes")

        graph = GraphDef(
            id=graph_id,
            name=name,
            nodes=nodes,
            edges=edges,
            start_node=start_node,
        )
        self.add_graph(graph)
        return graph

    # ---------------- Execution ----------------

    def run_graph(
        self,
        graph_id: str,
        initial_state: Optional[State] = None,
        max_steps: int = 100,
    ) -> RunRecord:
        if graph_id not in self.graphs:
            raise KeyError(f"Graph '{graph_id}' not found")

        graph = self.graphs[graph_id]
        state: State = dict(initial_state or {})

        run_id = str(uuid.uuid4())
        run = RunRecord(
            id=run_id,
            graph_id=graph_id,
            state=state,
            current_node=graph.start_node,
        )
        self.runs[run_id] = run

        step = 0
        tools = self.tools_registry.all()

        while run.current_node is not None and step < max_steps:
            node_def = graph.nodes[run.current_node]
            before = dict(run.state)

            # Node may optionally return a next-node override
            next_override = node_def.func(run.state, tools)

            after = dict(run.state)
            run.log.append(
                {
                    "step": step,
                    "node": node_def.name,
                    "before": before,
                    "after": after,
                    "next_override": next_override,
                }
            )

            if next_override is not None:
                # Branching / looping controlled by node
                run.current_node = next_override
            else:
                # Default transition
                run.current_node = graph.edges.get(node_def.name)

            step += 1

        run.finished = True
        run.finished_at = time.time()
        return run

    # ---------------- Introspection ----------------

    def get_run(self, run_id: str) -> RunRecord:
        if run_id not in self.runs:
            raise KeyError(f"Run '{run_id}' not found")
        return self.runs[run_id]
