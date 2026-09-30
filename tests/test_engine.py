import math
import numpy as np
import networkx as nx
import pytest
from graphlab.models import Graph, Edge, Parameters, BenchmarkRequest, parse_csv
from graphlab.engine import (generate, analyze, indexed, shortest_path, semiring_query,
                            vertex_partition, edge_partition, benchmark, fingerprint)


def reference(graph):
    result = nx.Graph()
    result.add_nodes_from(graph.nodes)
    result.add_weighted_edges_from((e.source, e.target, e.weight) for e in graph.edges)
    return result


@pytest.mark.parametrize('family', ['sample', 'hub', 'random', 'grid', 'disconnected'])
def test_dijkstra_against_networkx(family):
    graph = generate(family, 31, 17)
    ref = reference(graph)
    for source in graph.nodes[::4]:
        distances = nx.single_source_dijkstra_path_length(ref, source)
        for target in graph.nodes:
            result = shortest_path(graph, source, target)
            assert result['reachable'] == (target in distances)
            assert result['distance'] == distances.get(target)
            if result['reachable']:
                assert result['path'][0] == source and result['path'][-1] == target
                assert sum(ref[u][v]['weight'] for u, v in zip(result['path'], result['path'][1:])) == result['distance']


def test_zero_weight_edges_and_isolated_vertices():
    graph = Graph(nodes=['isolated'], edges=[Edge(source='A', target='B', weight=0), Edge(source='B', target='C', weight=2)])
    assert shortest_path(graph, 'A', 'B')['distance'] == 0
    assert shortest_path(graph, 'A', 'C')['distance'] == 2
    assert shortest_path(graph, 'A', 'isolated')['distance'] is None
    result = analyze(graph, Parameters())
    assert result['summary']['components'] == 2
    for part in result['partitions'][2:]:
        assert part['active_vertices'] == 3 and part['isolated_vertices'] == 1
        assert part['replication_factor'] == sum(map(len,part['replicas']))/3


@pytest.mark.parametrize('family', ['sample','grid','hub','disconnected'])
@pytest.mark.parametrize('capacity', [False, True])
def test_partition_integrity_and_scores(family, capacity):
    graph = generate(family, 51, 42)
    params = Parameters(partitions=4, capacity=capacity)
    edges, _ = indexed(graph)
    result = analyze(graph, params)
    for part in result['partitions']:
        assignments = part['assignments']
        assert all(0 <= p < 4 for p in assignments)
        assert len(assignments) == (len(graph.nodes) if part['kind']=='vertex' else len(edges))
        assert part['loads'] == [assignments.count(p) for p in range(4)]
        assert part['max_load_ratio'] == max(part['loads']) / (sum(part['loads'])/4)
        if part['kind'] == 'vertex':
            assert part['cut_edges'] == sum(assignments[u]!=assignments[v] for u,v,_ in edges)
        else:
            expected=[set() for _ in graph.nodes]
            for (u,v,_),p in zip(edges,assignments):
                expected[u].add(p);expected[v].add(p)
            assert part['replicas'] == [sorted(parts) for parts in expected]
            assert part['replication_factor'] == sum(map(len,expected)) / sum(bool(parts) for parts in expected)
        if capacity and part['algorithm'] in ('FENNEL','HDRF'):
            assert max(part['loads']) <= part['details']['load_cap']
        for entry in part['trace']:
            if entry['scores']:
                score=entry['scores'][entry['chosen']]
                assert score['eligible']
                assert score['score'] == max(s['score'] for s in entry['scores'] if s['eligible'])


def test_hdrf_exposes_replication_balance_tradeoff():
    graph=generate()
    low=edge_partition(graph,Parameters(balance_lambda=0),'HDRF')
    high=edge_partition(graph,Parameters(balance_lambda=8),'HDRF')
    assert low['loads'] == [12,0] and low['replication_factor']==1
    assert high['max_load_ratio'] < low['max_load_ratio']
    assert high['replication_factor'] > low['replication_factor']


@pytest.mark.parametrize('hops', [0,1,2,3,6])
def test_semirings_against_independent_references(hops):
    graph=generate()
    ref=reference(graph)
    matrix=nx.to_numpy_array(ref,nodelist=graph.nodes,weight=None,dtype=np.int64)
    counts=np.linalg.matrix_power(matrix,hops)
    for source in graph.nodes:
        distances={source:0}
        for _ in range(hops):
            previous=distances.copy()
            for u,v,weight in ref.edges.data('weight'):
                if u in previous: distances[v]=min(distances.get(v,math.inf),previous[u]+weight)
                if v in previous: distances[u]=min(distances.get(u,math.inf),previous[v]+weight)
        for target in graph.nodes:
            actual=semiring_query(graph,source,target,hops)
            u,v=graph.nodes.index(source),graph.nodes.index(target)
            assert actual['exact_hop_walks']==counts[u,v]
            assert actual['exact_hop_reachable']==bool(counts[u,v])
            assert actual['min_weight_up_to_hops']==distances.get(target)


def test_weighted_storage_accounting():
    result=analyze(generate(),Parameters())
    rows={row['name']:row for row in result['storage']['rows']}
    assert rows['Dense matrix']['payload_bytes']==8*8*8
    assert rows['Adjacency list']['payload_bytes']==2*12*16
    assert rows['CSR']['payload_bytes']==(8+1)*8+2*12*16
    assert rows['Edge list']['payload_bytes']==12*24
    assert result['storage']['csr_preview']['offsets'][-1]==24
    assert all(r['allocated_bytes_estimate']>=r['payload_bytes'] for r in rows.values())


@pytest.mark.parametrize('data', [
    b'source,target,weight\nA,B,-1\n', b'source,target,weight\nA,B,nan\n',
    b'source,target,weight\nA,B,inf\n', b'source,target,weight\nA,A,1\n',
    b'source,target,weight\nA,B,1\nB,A,2\n', b'source,target\nA,B\n',
    b'source,target,weight\nA,B\n', b'source,target,weight\nA,B,1,2\n',
    b'source,target,weight\n', b'\xff\xff', b'x'*1_000_001])
def test_csv_rejects_invalid_inputs(data):
    with pytest.raises(ValueError):parse_csv(data)


def test_csv_labels_bom_and_zero_weight():
    graph=parse_csv('\ufeffsource,target,weight\n"Frankfurt, Main",Bayreuth,0\nBayreuth,München,2.5\n'.encode())
    assert graph.nodes==['Frankfurt, Main','Bayreuth','München']
    assert shortest_path(graph,'Frankfurt, Main','München')['distance']==2.5


@pytest.mark.parametrize('family', ['hub','random','grid','disconnected'])
def test_benchmark_determinism_and_actual_sizes(family):
    request=BenchmarkRequest(family=family,sizes=[8,16],repeats=2)
    a,b=benchmark(request),benchmark(request)
    assert len(a['rows'])==8
    for left,right in zip(a['rows'],b['rows']):
        assert left['fingerprint']==right['fingerprint']==fingerprint(generate(family,left['vertices'],42))
        assert left['loads']==right['loads']
        assert left['min_ms']<=left['median_ms']<=left['max_ms']
        assert left['dense_payload_bytes']==left['vertices']**2*8


def test_empty_graph_and_matrix_limits():
    graph=Graph(nodes=['A','B'])
    result=analyze(graph,Parameters())
    assert result['summary']['components']==2
    assert result['partitions'][-1]['replication_factor'] is None
    assert shortest_path(graph,'A','B')['path']==[]
    assert semiring_query(generate('grid',65),'0','1',3)['available'] is False
    with pytest.raises(ValueError):analyze(generate(),Parameters(partitions=8).model_copy(update={'partitions':9}))


def test_legacy_semiring_zero_and_negative_powers():
    import module2_semirings as m
    a=m.build_unweighted_matrix();w=m.build_weighted_matrix()
    assert np.array_equal(m.standard_power(a,0),np.eye(8))
    assert np.array_equal(m.anypair_power(a,0),np.eye(8,dtype=bool))
    identity=np.full((8,8),math.inf);np.fill_diagonal(identity,0)
    assert np.array_equal(m.minplus_power(w,0),identity)
    for function in [m.standard_power,m.anypair_power,m.minplus_power]:
        with pytest.raises(ValueError):function(a,-1)
