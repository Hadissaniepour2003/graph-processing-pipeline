# Graph Processing Pipeline

A Python project exploring core concepts in distributed graph processing,
built alongside the Graph Processing & Machine Learning course at the
University of Bayreuth.

## Background

Graphs show up everywhere — social networks, road maps, protein interactions,
the web. As these graphs grow to billions of nodes and trillions of edges,
three questions become critical:

- How do you store a graph efficiently?
- How do you compute on it?
- How do you split it across multiple machines?

This project works through each of these questions with concrete
implementations and visualizations, using the same small graph throughout
so the progression is easy to follow.

## What's Inside

**Module 1 — Storage Structures**
Four ways to store a graph: adjacency matrix, adjacency list, CSR, and
edge list. Each has different memory and access trade-offs. The comparison
makes it clear why CSR is the standard for large-scale processing.

**Module 2 — Semiring Matrix Multiplication**
Matrix powers can answer graph questions, but only if you use the right
operators. This module implements three semirings on the same graph:
- Standard: how many paths of exactly n hops exist?
- Any-Pair: does any path of n hops exist?
- Min-Plus: what is the shortest weighted path?

**Module 3 — Vertex Partitioning**
Splitting a graph across machines while keeping communication costs low.
Two approaches compared side by side — FENNEL (streaming) and Label
Propagation (distributed majority vote) — with cut edges and balance
both measured.

**Module 4 — Edge Partitioning**
For graphs with high-degree hub vertices, assigning edges to machines
works better than assigning vertices. DBH and HDRF are both implemented
and their replication factors compared.

## Setup

```bash
pip install -r requirements.txt
```

## Running

Full pipeline:
```bash
python main.py
```

Individual modules:
```bash
python module1_storage.py
python module2_semirings.py
python module3_vertex_partition.py
python module4_edge_partition.py
```

## Project Structure

## Output

Running each module produces a PNG saved to the project folder:

- graph_visualization.png
- memory_comparison.png
- shortest_paths.png
- vertex_partitioning.png
- edge_partitioning.png

## Some Results Worth Noting

The adjacency matrix uses 64 cells for an 8-vertex graph. The edge list
uses 12. The difference grows quadratically as the graph scales.

The Min-Plus semiring finds that the path from vertex 0 to vertex 2
costs 3 going through vertex 1, despite a direct edge costing 4.

FENNEL produces a balanced partition with 2 cut edges. Label Propagation
finds a partition with 0 cut edges but puts all 8 vertices on one side,
which defeats the purpose of partitioning entirely.

HDRF achieves a replication factor of 1.0 on this graph. DBH reaches 1.5
due to its stateless nature causing unnecessary replication.

## References

- Malewicz et al. Pregel: A System for Large-Scale Graph Processing. 2010.
- Tsourakakis et al. FENNEL: Streaming Graph Partitioning for Massive Scale Graphs. 2014.
- Petroni et al. HDRF: Stream-Based Partitioning for Power-Law Graphs. 2015.
- Valiant. A Bridging Model for Parallel Computation. 1990.