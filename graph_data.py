# graph_data.py
# Defines the shared graph used across all modules
# 8 vertices, 12 weighted edges, 2 communities

# Number of vertices
NUM_VERTICES = 8

# Edge list with weights: (vertex_i, vertex_j, weight)
EDGES = [
    (0, 1, 2),
    (0, 2, 4),
    (1, 2, 1),
    (1, 3, 3),
    (2, 3, 5),
    (3, 4, 2),
    (3, 5, 6),
    (4, 5, 1),
    (4, 6, 3),
    (5, 6, 2),
    (5, 7, 4),
    (6, 7, 1),
]

# Ground truth community labels for each vertex
COMMUNITIES = {
    0: 'A', 1: 'A', 2: 'A', 3: 'A',
    4: 'B', 5: 'B', 6: 'B', 7: 'B'
}

# Fixed node positions for consistent visualization across all modules
POSITIONS = {
    0: (0, 2),
    1: (1, 3),
    2: (1, 1),
    3: (2, 2),
    4: (4, 2),
    5: (5, 3),
    6: (5, 1),
    7: (6, 2),
}