"""Own graph algorithms. NetworkX is used only as an independent test reference."""
from collections import Counter
import hashlib
import heapq
import json
import math
import platform
import random
import statistics
import sys
import time
import numpy as np
from .models import Graph, Edge, Parameters, BenchmarkRequest


def indexed(graph):
    lookup = {v: i for i, v in enumerate(graph.nodes)}
    edges = [(lookup[e.source], lookup[e.target], e.weight) for e in graph.edges]
    adjacency = [[] for _ in graph.nodes]
    for u, v, w in edges:
        adjacency[u].append((v, w))
        adjacency[v].append((u, w))
    return edges, adjacency


def fingerprint(graph):
    return hashlib.sha256(json.dumps(graph.model_dump(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def allocated_bytes(value, seen=None):
    """Approximate owned Python allocation; counts shared objects once, not process RSS."""
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(allocated_bytes(k, seen) + allocated_bytes(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple)):
        size += sum(allocated_bytes(item, seen) for item in value)
    return size


def storage(graph):
    n = len(graph.nodes)
    edges, adjacency = indexed(graph)
    # Every representation retains weights. All indices and values occupy 8 bytes.
    dense = np.full((n, n), np.inf, dtype=np.float64)
    np.fill_diagonal(dense, 0)
    for u, v, w in edges:
        dense[u, v] = dense[v, u] = w
    dtype = np.dtype([('vertex', '<i8'), ('weight', '<f8')])
    lists = [np.array(neighbors, dtype=dtype) for neighbors in adjacency]
    offsets = np.zeros(n + 1, dtype=np.int64)
    for i, neighbors in enumerate(adjacency):
        offsets[i + 1] = offsets[i] + len(neighbors)
    columns = np.array([v for neighbors in adjacency for v, _ in neighbors], dtype=np.int64)
    weights = np.array([w for neighbors in adjacency for _, w in neighbors], dtype=np.float64)
    csr = (offsets, columns, weights)
    edge_dtype = np.dtype([('source', '<i8'), ('target', '<i8'), ('weight', '<f8')])
    edge_array = np.array(edges, dtype=edge_dtype)
    representations = [('Dense matrix', dense, dense.nbytes),
                       ('Adjacency list', lists, sum(a.nbytes for a in lists)),
                       ('CSR', csr, sum(a.nbytes for a in csr)),
                       ('Edge list', edge_array, edge_array.nbytes)]
    return {'rows': [{'name': name, 'payload_bytes': int(payload),
                      'allocated_bytes_estimate': allocated_bytes(value)} for name, value, payload in representations],
            'method': 'Numeric payload uses int64 indices and float64 weights. Undirected adjacency list and CSR store each edge twice; the edge list stores it once. List row containers, label strings and Python object headers are excluded from payload. Allocation estimates include representation containers and headers via sys.getsizeof, count shared objects once, and are not total process memory.',
            'csr_preview': {'offsets': offsets[:21].tolist(), 'columns': columns[:40].tolist(), 'weights': weights[:40].tolist(), 'truncated': n > 20 or len(columns) > 40}}


def load_metrics(loads):
    ideal = sum(loads) / len(loads)
    return {'loads': loads, 'max_load_ratio': max(loads) / ideal if ideal else None,
            'used_partitions': sum(load > 0 for load in loads)}


def vertex_partition(graph, params, method):
    n = len(graph.nodes)
    k = params.partitions
    edges, adj = indexed(graph)
    sizes = [0] * k
    assignments = [-1] * n
    trace = []
    status = 'single streaming pass'
    if method == 'FENNEL':
        gamma = 1.5
        alpha = len(edges) * math.sqrt(k) / n ** gamma
        limit = math.ceil(1.1 * math.ceil(n / k)) if params.capacity else n
        for v in range(n):
            scores = []
            for p in range(k):
                locality = sum(assignments[u] == p for u, _ in adj[v])
                penalty = alpha * ((sizes[p] + 1) ** gamma - sizes[p] ** gamma)
                scores.append({'partition': p, 'locality': locality, 'penalty': penalty,
                               'score': locality - penalty, 'eligible': sizes[p] < limit})
            chosen = max((p for p in range(k) if sizes[p] < limit), key=lambda p: (scores[p]['score'], -sizes[p], -p))
            assignments[v] = chosen
            sizes[chosen] += 1
            if v < 100:
                trace.append({'vertex': graph.nodes[v], 'chosen': chosen, 'scores': scores})
        extra = {'alpha': alpha, 'gamma': gamma, 'load_cap': limit if params.capacity else None}
    else:
        rng = random.Random(params.seed)
        assignments = [rng.randrange(k) for _ in range(n)]
        seen = {tuple(assignments)}
        status = 'iteration limit reached'
        for iteration in range(1, 101):
            next_labels = assignments.copy()
            for v in range(n):
                counts = Counter(assignments[u] for u, _ in adj[v])
                if counts:
                    highest = max(counts.values())
                    winners = [p for p, count in counts.items() if count == highest]
                    if len(winners) == 1:
                        next_labels[v] = winners[0]
            if next_labels == assignments:
                status = 'converged'
                break
            assignments = next_labels
            if tuple(assignments) in seen:
                status = 'cycle detected'
                break
            seen.add(tuple(assignments))
        sizes = [assignments.count(p) for p in range(k)]
        extra = {'iterations': iteration, 'note': 'Synchronous community baseline; it has no load-balance constraint and can collapse or cycle.'}
    cuts = sum(assignments[u] != assignments[v] for u, v, _ in edges)
    return {'algorithm': method, 'kind': 'vertex', **load_metrics(sizes), 'cut_edges': cuts,
            'cut_fraction': cuts / len(edges) if edges else 0, 'assignments': assignments,
            'status': status, 'details': extra, 'trace': trace}


def edge_partition(graph, params, method):
    edges, adj = indexed(graph)
    k = params.partitions
    loads = [0] * k
    replicas = [set() for _ in graph.nodes]
    assignments = []
    trace = []
    limit = math.ceil(1.1 * math.ceil(len(edges) / k)) if params.capacity else len(edges)
    for i, (u, v, _) in enumerate(edges):
        du, dv = len(adj[u]), len(adj[v])
        if method == 'DBH':
            anchor = u if du < dv else v
            digest = hashlib.blake2b(graph.nodes[anchor].encode(), digest_size=8).digest()
            chosen = int.from_bytes(digest, 'big') % k
            scores = []
        else:
            hi, lo = max(loads), min(loads)
            scores = []
            for p in range(k):
                locality = (1 + dv / (du + dv) if p in replicas[u] else 0) + (1 + du / (du + dv) if p in replicas[v] else 0)
                balance = params.balance_lambda * (hi - loads[p]) / (1 + hi - lo)
                scores.append({'partition': p, 'locality': locality, 'balance': balance,
                               'score': locality + balance, 'eligible': loads[p] < limit})
            chosen = max((p for p in range(k) if loads[p] < limit), key=lambda p: (scores[p]['score'], -loads[p], -p))
        assignments.append(chosen)
        loads[chosen] += 1
        replicas[u].add(chosen)
        replicas[v].add(chosen)
        if i < 100:
            trace.append({'edge_index': i, 'source': graph.nodes[u], 'target': graph.nodes[v],
                          'chosen': chosen, 'scores': scores,
                          'hash_vertex': graph.nodes[anchor] if method == 'DBH' else None})
    active = sum(bool(neighbors) for neighbors in adj)
    appearances = sum(len(parts) for parts in replicas)
    return {'algorithm': method, 'kind': 'edge', **load_metrics(loads), 'assignments': assignments,
            'replication_factor': appearances / active if active else None,
            'active_vertices': active, 'isolated_vertices': len(graph.nodes) - active,
            'replicated_vertices': sum(len(parts) > 1 for parts in replicas),
            'replicas': [sorted(parts) for parts in replicas], 'trace': trace,
            'details': {'load_cap': limit if params.capacity and method == 'HDRF' else None,
                        'note': 'Full-graph degrees are known before streaming. Capacity applies to HDRF only; DBH is a hash baseline.'}}


def partition_results(graph, params):
    if params.partitions > len(graph.nodes):
        raise ValueError('Partition count cannot exceed the number of vertices.')
    results = []
    for method in ('FENNEL', 'Label propagation', 'DBH', 'HDRF'):
        start = time.perf_counter_ns()
        result = vertex_partition(graph, params, method) if method in ('FENNEL', 'Label propagation') else edge_partition(graph, params, method)
        result['runtime_ms'] = (time.perf_counter_ns() - start) / 1e6
        results.append(result)
    return results


def analyze(graph, params):
    edges, adj = indexed(graph)
    visited = set()
    components = 0
    for vertex in range(len(graph.nodes)):
        if vertex not in visited:
            components += 1
            stack = [vertex]
            visited.add(vertex)
            while stack:
                for neighbor, _ in adj[stack.pop()]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
    return {'graph': graph.model_dump(), 'parameters': params.model_dump(), 'fingerprint': fingerprint(graph),
            'summary': {'vertices': len(graph.nodes), 'edges': len(edges), 'components': components,
                        'density': 2 * len(edges) / (len(graph.nodes) * (len(graph.nodes)-1)) if len(graph.nodes) > 1 else 0,
                        'max_degree': max(map(len, adj), default=0)},
            'storage': storage(graph), 'partitions': partition_results(graph, params)}


def shortest_path(graph, source, target):
    if source not in graph.nodes or target not in graph.nodes:
        raise ValueError('Choose source and target vertices from the current graph.')
    _, adj = indexed(graph)
    start, end = graph.nodes.index(source), graph.nodes.index(target)
    distances = [math.inf] * len(adj)
    previous = [None] * len(adj)
    distances[start] = 0
    queue = [(0, start)]
    while queue:
        distance, vertex = heapq.heappop(queue)
        if distance != distances[vertex]:
            continue
        if vertex == end:
            break
        for neighbor, weight in adj[vertex]:
            candidate = distance + weight
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                previous[neighbor] = vertex
                heapq.heappush(queue, (candidate, neighbor))
    path = []
    if math.isfinite(distances[end]):
        vertex = end
        while vertex is not None:
            path.append(graph.nodes[vertex])
            vertex = previous[vertex]
        path.reverse()
    return {'reachable': bool(path), 'distance': distances[end] if path else None, 'path': path, 'algorithm': 'Dijkstra (own implementation)'}


def semiring_query(graph, source, target, hops):
    if len(graph.nodes) > 64:
        return {'available': False, 'reason': 'Matrix experiments are limited to 64 vertices. Dijkstra remains available for the full graph.'}
    if source not in graph.nodes or target not in graph.nodes:
        raise ValueError('Unknown vertex label.')
    n = len(graph.nodes)
    edges, _ = indexed(graph)
    counts = np.zeros((n, n), dtype=np.int64)
    weighted = np.full((n, n), np.inf)
    np.fill_diagonal(weighted, 0)
    for u, v, w in edges:
        counts[u, v] = counts[v, u] = 1
        weighted[u, v] = weighted[v, u] = w
    # Multiplicative identities make the zero-hop case precise.
    count_power = np.eye(n, dtype=np.int64)
    reach = np.eye(n, dtype=bool)
    minimum = np.full((n, n), np.inf)
    np.fill_diagonal(minimum, 0)
    for _ in range(hops):
        count_power = count_power @ counts
        reach = reach @ (counts > 0)
        next_minimum = np.full((n, n), np.inf)
        for k in range(n):
            next_minimum = np.minimum(next_minimum, minimum[:, k, None] + weighted[k, None, :])
        minimum = next_minimum
    u, v = graph.nodes.index(source), graph.nodes.index(target)
    value = float(minimum[u, v])
    return {'available': True, 'hops': hops, 'exact_hop_walks': int(count_power[u, v]),
            'exact_hop_reachable': bool(reach[u, v]), 'min_weight_up_to_hops': value if math.isfinite(value) else None,
            'explanation': 'Standard multiplication counts walks of exactly h edges, allowing revisits. Boolean multiplication tests the same exact-hop reachability. Min-plus includes zero-cost diagonal stays, so its result is the minimum weight using at most h edges.'}


def generate(family='sample', size=24, seed=42):
    from graph_data import EDGES
    if family == 'sample':
        return Graph(nodes=[str(i) for i in range(8)], edges=[Edge(source=str(u), target=str(v), weight=w) for u, v, w in EDGES])
    if family not in ('random', 'grid', 'hub', 'disconnected') or not 2 <= size <= 1000:
        raise ValueError('Choose sample, random, grid, hub or disconnected; size must be 2–1000.')
    rng = random.Random(seed)
    pairs = set()
    if family == 'grid':
        width = math.ceil(math.sqrt(size))
        for v in range(size):
            if v % width and v - 1 >= 0:
                pairs.add((v-1, v))
            if v >= width:
                pairs.add((v-width, v))
    elif family == 'hub':
        # Seeded preferential attachment, two distinct earlier neighbors per vertex.
        urn = [0]
        for v in range(1, size):
            targets = set()
            while len(targets) < min(2, v):
                targets.add(rng.choice(urn))
            for u in sorted(targets):
                pairs.add((u, v))
                urn.extend((u, v))
    else:
        # A chain per component guarantees connectivity before adding random edges.
        groups = [list(range(size))] if family == 'random' else [list(range(size//2)), list(range(size//2, size))]
        for group in groups:
            pairs.update(zip(group, group[1:]))
            target = min(3 * len(group), len(group) * (len(group)-1)//2)
            local = {pair for pair in pairs if pair[0] in group}
            while len(local) < target:
                u, v = sorted(rng.sample(group, 2))
                local.add((u, v))
            pairs.update(local)
    return Graph(nodes=[str(v) for v in range(size)], edges=[Edge(source=str(u), target=str(v), weight=rng.randint(1, 9)) for u, v in sorted(pairs)])


def benchmark(request: BenchmarkRequest):
    rows = []
    for size in request.sizes:
        graph = generate(request.family, size, request.parameters.seed)
        # One untimed warmup; repeats time the same graph, not changing workloads.
        partition_results(graph, request.parameters)
        samples = [partition_results(graph, request.parameters) for _ in range(request.repeats)]
        storage_rows = storage(graph)['rows']
        for index, result in enumerate(samples[0]):
            rows.append({'vertices': size, 'edges': len(graph.edges), 'algorithm': result['algorithm'],
                         'median_ms': statistics.median(s[index]['runtime_ms'] for s in samples),
                         'min_ms': min(s[index]['runtime_ms'] for s in samples),
                         'max_ms': max(s[index]['runtime_ms'] for s in samples),
                         'max_load_ratio': result['max_load_ratio'], 'loads': result['loads'],
                         'cut_fraction': result.get('cut_fraction'), 'replication_factor': result.get('replication_factor'),
                         'csr_payload_bytes': next(r['payload_bytes'] for r in storage_rows if r['name'] == 'CSR'),
                         'dense_payload_bytes': storage_rows[0]['payload_bytes'], 'fingerprint': fingerprint(graph)})
    return {'type': 'benchmark', 'request': request.model_dump(), 'rows': rows,
            'environment': {'python': platform.python_version(), 'platform': platform.platform(), 'numpy': np.__version__},
            'method': 'One untimed warmup, then repeated sequential runs of the same seeded graph. Median/min/max use perf_counter_ns. Timings include scoring and trace creation, exclude generation, storage construction, HTTP and rendering. This is a local simulation; results depend on hardware and process load.'}
