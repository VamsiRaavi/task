Mini Workflow Engine (LangGraph-Lite)
A minimal workflow/agent engine inspired by LangGraph, implemented with Python and FastAPI.
This engine demonstrates the foundations of agentic workflows:
Nodes (Python functions)
Stateful execution
Static edges (default graph flow)
Dynamic branching (node decides next step)
Looping (repeat nodes until conditions met)
Execution logs (full trace of each step)
A complete example workflow — Code Review Mini-Agent — is included to demonstrate the engine.
📦 Features
✔ Nodes as functions
Each node is a Python function that reads/modifies a shared state dict.
✔ Shared state passing
Nodes communicate only through a mutable state object.
✔ Static edges
Define a fixed workflow structure like:
extract → check_complexity → detect_issues → suggest_improvements → evaluate_quality
✔ Branching
A node can override the next step:
return "suggest_improvements"
✔ Looping
Nodes can jump back to earlier nodes, enabling retry/refinement loops.
✔ Execution log
Every step logs:
node name
state before
state after
override transitions
✔ FastAPI APIs
Everything is exposed over HTTP:
Method	Route	Description
POST	/graph/create	Create a new graph
POST	/graph/run	Run graph synchronously
GET	/graph/state/{run_id}	Retrieve saved run state & logs
🧱 Architecture Overview
<p align="center"> <img src="docs/diagram-architecture.svg" width="650" /> </p>
🧬 Graph Model
A workflow (graph) consists of:
Nodes: { name: NodeDef }
Edges: { node_name → next_node_or_null }
Start node: entry point of execution
State: mutable dictionary passed to every node
Node signature:
def node_name(state: dict, tools: dict) -> str | None:
If a node returns:
"some_node" → engine dynamically goes there (branching)
None → engine follows the static edges mapping (default path)
This mechanism enables both branching & looping.
🧪 Built-In Example: Code Review Mini-Agent
The included workflow demonstrates:
State-based branching
Iterative refinement loop
Simple static edges
Logging
<p align="center"> <img src="docs/diagram-code-review.svg" width="650" /> </p>
Execution Flow
extract
Find function names in the code.
check_complexity
Compute simple complexity metrics.
detect_issues
Identify issues like TODO, print(), wildcard imports, long files.
suggest_improvements
Generate combined suggestions + a quality_score.
evaluate_quality
Decide:
stop if quality good enough
stop if too many iterations
else loop back to suggest_improvements
🚀 How to Run
1. Install dependencies
pip install fastapi uvicorn
2. Directory structure
.
├── app
│   ├── __init__.py
│   ├── engine.py
│   ├── workflows.py
│   └── main.py
└── README.md
3. Start FastAPI
uvicorn app.main:app --reload
Server runs at:
http://127.0.0.1:8000
4. Open Swagger (API UI)
http://127.0.0.1:8000/docs
You can:
Run workflows
Create custom workflows
Inspect run logs
🧪 Running the Example Workflow
Use this body in POST /graph/run:
{
  "graph_id": "code_review",
  "initial_state": {
    "code": "def add(a, b):\n    print(a+b)\n    return a+b\n",
    "threshold": 0.8,
    "max_loops": 3
  }
}
Example response:
{
  "run_id": "1234-uuid",
  "final_state": {
    "functions": ["add"],
    "complexity": {...},
    "issues": [...],
    "quality_score": 0.47,
    "iterations": 1,
    "status": "stopped_max_loops"
  },
  "log": [
    {"step":0,"node":"extract", ...},
    {"step":1,"node":"check_complexity", ...},
    ...
  ]
}
Retrieve history later:
GET /graph/state/{run_id}
🛠 Creating Custom Graphs
Example body for /graph/create:
{
  "name": "quick_complexity_check",
  "nodes": [
    {"name": "extract", "function": "extract"},
    {"name": "check_complexity", "function": "check_complexity"}
  ],
  "edges": {
    "extract": "check_complexity",
    "check_complexity": null
  },
  "start_node": "extract"
}
Use returned graph_id with /graph/run.
🧪 Testing (Optional)
from fastapi.testclient import TestClient
from app.main import app, CODE_REVIEW_GRAPH_ID

client = TestClient(app)

def test_run_code_review():
    payload = {
        "graph_id": CODE_REVIEW_GRAPH_ID,
        "initial_state": {
            "code": "def foo(): return 1"
        }
    }
    resp = client.post("/graph/run", json=payload)
    assert resp.status_code == 200
    assert "run_id" in resp.json()
Run:
pytest
🚧 What I Would Improve With More Time
1️⃣ Async execution
Support async def nodes + non-blocking I/O for long-running tasks.
2️⃣ WebSocket real-time streaming
Live stream node-by-node logs:
Useful for debugging
Ideal for visual graph UIs
3️⃣ Persistence layer
Store graphs & runs in SQLite/Postgres instead of in-memory.
4️⃣ Visual graph builder
Drag-and-drop UI to compose nodes & edges.
5️⃣ Error routing
Define special edges for failures:
node → on_error → fallback_node
6️⃣ Parallelism
Future feature: allow branching across multiple nodes at once.
7️⃣ More real-world workflows
Summarization and refinement
Data quality pipeline
ETL validations