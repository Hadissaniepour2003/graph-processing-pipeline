# Graph Processing Pipeline · Graph Lab

[![Verification](https://github.com/Hadissaniepour2003/graph-processing-pipeline/actions/workflows/verify.yml/badge.svg)](https://github.com/Hadissaniepour2003/graph-processing-pipeline/actions/workflows/verify.yml)

This project started alongside the Graph Processing & Machine Learning course at the University of Bayreuth. The original question was simple: how do you store a graph, compute on it, and split the work without creating unnecessary communication?

Graph Lab turns those exercises into a small application where you can bring your own graph and inspect the results. Upload a weighted CSV, compare four partitioning algorithms, follow a shortest route, and run repeatable benchmarks. The browser sends requests to a real **FastAPI backend**; calculations run in Python and completed experiments are saved in **SQLite**.

It is a **local simulation of graph-processing concepts**. Partition colors represent assignments, not separate running machines. That distinction matters when talking about performance.

## Start on Windows

1. Install **Python 3.12 or newer** from [python.org](https://www.python.org/downloads/windows/). Tick **Add python.exe to PATH** in the installer.
2. Download this repository with **Code → Download ZIP**, then extract it. If you downloaded an older version, get a fresh ZIP.
3. Open the extracted project folder and double-click **Start-GraphLab.cmd**.
4. Keep the terminal window open. After setup, your browser opens **[http://localhost:8000/](http://localhost:8000/)**.

The first launch needs internet access to install dependencies. The application itself then works locally, including the graph examples, algorithms, exports, and API documentation. No API key or Node.js installation is needed.

`localhost` refers to the computer running the app. The link works while the server is running; it is not a publicly hosted demo.

If Windows asks whether to run a downloaded script, review `Start-GraphLab.cmd` first. It creates a project environment, installs the pinned dependencies, and starts `run_lab.py`.

## Start from a terminal

Run these commands **inside the extracted project folder**, where `requirements.txt` and `run_lab.py` are located.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_lab.py
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_lab.py
```

If port 8000 is occupied, close the previous Graph Lab terminal or start with `run_lab.py --port 8001`. Then use [http://localhost:8001/](http://localhost:8001/). Press Ctrl+C in the terminal to stop the server.

## What you can do

- **Import your graph.** Upload or paste a CSV with arbitrary vertex labels and nonnegative weights. Invalid rows produce a useful error without replacing your current results.
- **Compare storage.** See actual numeric buffer sizes for a weighted dense matrix, adjacency list, CSR, and edge list. A separate Python allocation estimate includes containers and object headers. The app explains the measurement method.
- **Compare partitioning.** FENNEL and label propagation assign vertices; DBH and HDRF assign edges. Inspect partition loads, cross-partition cuts, replication, and computation time.
- **Explore decisions.** Step through the first 100 placements and see locality, balance penalties, eligible partitions, and the chosen score. Change HDRF’s balance parameter and rerun the graph.
- **Calculate routes.** An independent Dijkstra implementation returns an actual shortest path and highlights it on the map. Matrix experiments distinguish exact-hop walks, Boolean reachability, and minimum weight within a hop limit.
- **Benchmark repeatably.** Choose a graph family, sizes, seed, and repeat count. Compare measured median/min/max runtimes and quality metrics; export the actual results as CSV or JSON.
- **Reopen your work.** The latest 50 completed analyses and benchmarks survive a server restart in a local SQLite database.

## CSV format

The header must be exactly `source,target,weight`:

```csv
source,target,weight
Bayreuth,Nuremberg,2
Nuremberg,Munich,3
Bayreuth,Munich,8
```

The shortest route from Bayreuth to Munich has weight **5**, via Nuremberg. Weights are abstract costs; this example does not claim real travel distances.

Use UTF-8, including UTF-8 with BOM. Labels can contain spaces and Unicode; quote labels containing commas. Edges are undirected, so `A,B` and `B,A` represent the same edge. Self-loops, duplicate edges, negative or nonfinite weights, and values above 1,000,000,000 are rejected. CSV supports up to **1 MB**, **1,000 vertices**, and **5,000 edges**. JSON input can explicitly include isolated vertices.

## A two-minute demo

1. Open the original **8-vertex / 12-edge** graph. In Storage, compare **512 B** for the dense numeric matrix, **456 B** for CSR, and **288 B** for the edge list. These are weighted buffer sizes, not vague “cells” or full process memory.
2. In Overview, inspect HDRF with λ = **1.1**: replication is **1.0**, but loads are **12 / 0**. A low replication score alone would hide a bad workload split.
3. Set λ = **8**, then click **Run analysis**. Loads become **6 / 6**. Inspect the new replication factor and step through Decisions to see why placements changed.
4. In Paths & semirings, choose **0 → 2**, with a hop limit of **2**. The shortest route is **0 → 1 → 2**, costing **3**, even though the direct edge costs 4. Explain why counting walks differs from finding minimum cost.
5. Run a seeded hub benchmark with **16,64,128,256** vertices and export its CSV. Reopen it from History.

A useful way to describe the project: “I took graph-processing coursework and extended it into a local experiment tool with input validation, a Python API, persistent results, and independent correctness checks. It lets me explain the trade-off between balance, communication, and storage using computed evidence.”

## How the calculations work

| Algorithm | Implementation in this lab | Important limit |
|---|---|---|
| FENNEL | Streaming vertex placement with exact marginal cost `α((s+1)^γ − s^γ)`, `γ=1.5`, `α=m√k/n^1.5` | This finite-difference variant uses vertex counts and unweighted locality; input order affects placement. |
| Label propagation | Seeded initialization, synchronous majority updates, retain current label on ties | Community baseline with no balance guarantee. Stops on convergence, a repeated state, or 100 iterations. |
| DBH | Hash the lower-degree endpoint with stable BLAKE2b; equal degrees choose the target | Stateless hash baseline. Label spelling and edge orientation can change placement. |
| HDRF | Endpoint locality plus `λ(maxLoad−load)/(1+maxLoad−minLoad)` | Full-graph degrees are known beforehand; this is not a strict online-degree implementation. |

FENNEL and HDRF break score ties by lower load, then partition ID. Enabling the load cap excludes full partitions: cap = `ceil(1.1 × ceil(item_count/k))`. The cap is an explicit variant and can exceed 10% slack on very small graphs due to integer rounding. DBH and label propagation remain unconstrained baselines.

Partitioning operates on graph topology, not edge weights. Storage and shortest paths retain and use the weights. Replication factor divides the number of vertex copies by **active vertices**; isolated vertices are reported separately. Max/ideal load means `max(partition_loads) / (total_items/k)`: 1 is ideal, larger values show imbalance. An empty edge graph has no meaningful edge replication or load ratio, so those metrics are null.

Standard matrix powers count **walks of exactly h edges**, including revisits. Boolean powers test exact-hop reachability. Min-plus uses a zero diagonal, so it finds minimum cost using **at most h edges**. All three implement the zero-hop identity. Matrix experiments are limited to **64 vertices and 6 hops**; Dijkstra remains available for the full graph. Interactive SVG drawing stops beyond **120 vertices or 500 edges**, while computations and exports include the entire graph.

Benchmarks use seeded random, grid, hub/preferential-attachment, or disconnected graph generators, up to five sizes between 8 and 512 vertices. Each size has one untimed warmup followed by 1–5 repeated runs of the same graph. Timing uses `perf_counter_ns` and includes scoring plus trace creation, but excludes graph generation, storage construction, HTTP, and rendering. Results include input fingerprints and environment metadata. Hardware and process load affect timing; these measurements do not establish distributed speedups.

## API and persistence

Open **[http://localhost:8000/docs](http://localhost:8000/docs)** for the locally served API explorer. The machine-readable schema is at `/openapi.json`. Documentation assets do not need a CDN.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Server readiness |
| `GET /api/example?family=hub&size=24&seed=42` | Deterministic graph input |
| `POST /api/import` | Multipart CSV, field name `file` |
| `POST /api/analyze` | JSON `{graph, parameters}`; compute and save |
| `POST /api/path` | JSON `{graph, source, target, hops}` |
| `POST /api/benchmark` | JSON `{family, sizes, repeats, parameters}`; compute and save |
| `GET /api/runs` | Latest 50 saved experiments |
| `GET /api/runs/{id}` | Reopen full computed results |
| `GET /api/runs/{id}/export?format=csv` | CSV export; `json` also supported |

The server binds to **127.0.0.1**. There is no account system; this is a local application. JSON bodies are bounded to 2 MB and graph validation is enforced by Pydantic. Experiment history is stored in `.data/experiments.sqlite`, excluded from Git. Copy the `.data` folder if moving your saved experiments to a fresh download. `GRAPHLAB_DATA_DIR` can override the data location.

## Tests and original coursework

Install development dependencies into the same Python environment:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest -q
```

On Windows, use `.venv\Scripts\python.exe` for `python`; on macOS/Linux, use `.venv/bin/python`. Linux may need `python -m playwright install --with-deps chromium` for browser system dependencies. `python -m pytest -q -m "not browser"` runs calculation/API checks without a browser installation.

The suite compares shortest paths to **NetworkX**, checks semirings against independent matrix and bounded-path references, verifies partition coverage and replica accounting, tests CSV/API validation and SQLite history, and exercises uploads, route calculations, λ changes, capacity, score inspection, exports, benchmarks, history, mobile layout, and the API explorer in **real Chromium**. GitHub Actions runs the suite on **Windows and Linux** and executes the original coursework pipeline.

The original modules remain available:

```bash
python main.py
```

This generates `graph_visualization.png`, `memory_comparison.png`, `shortest_paths.png`, `vertex_partitioning.png`, and `edge_partitioning.png`. The legacy storage builders expose an unweighted topology projection; their memory chart now uses the shared lab’s weighted buffer comparison. The original figures committed before Graph Lab are historical; regenerate them to see the current algorithms. For a headless machine, set `MPLBACKEND=Agg`.

```text
graphlab/models.py       bounded graph inputs and CSV parsing
graphlab/engine.py       storage, partitioning, routes, semirings, benchmarks
graphlab/api.py          FastAPI endpoints and SQLite history
graphlab/web/            offline HTML, CSS, JavaScript and API explorer
run_lab.py               local server and browser launcher
Start-GraphLab.cmd       Windows setup and startup
tests/                   calculation, API and browser checks
module1_storage.py       original coursework storage demonstrations
module2_semirings.py     original semiring demonstrations
module3_vertex_partition.py
module4_edge_partition.py
```

Possible next steps are weighted partition objectives, comparisons with established partitioners, larger sparse-matrix experiments, and measuring execution across actual workers. Those would require separate implementation and validation.

## References

- Tsourakakis et al., [FENNEL: Streaming Graph Partitioning for Massive Scale Graphs](https://math.cmu.edu/~ctsourak/fennel-wsdm.pdf), 2014.
- Petroni et al., *HDRF: Stream-Based Partitioning for Power-Law Graphs*, 2015.
- Malewicz et al., *Pregel: A System for Large-Scale Graph Processing*, 2010.
- Valiant, *A Bridging Model for Parallel Computation*, 1990.
