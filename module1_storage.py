# module1_storage.py
# Implements and compares all 4 graph storage structures
# Adjacency Matrix, Adjacency List, CSR, Edge List

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from graph_data import NUM_VERTICES, EDGES, POSITIONS

def build_adjacency_matrix():
    # Create n x n matrix filled with zeros
    matrix = np.zeros((NUM_VERTICES, NUM_VERTICES), dtype=int)
    
    # Fill in 1 where edge exists
    for (i, j, weight) in EDGES:
        matrix[i][j] = 1
        matrix[j][i] = 1  # undirected graph - both directions
    
    return matrix
def build_adjacency_list():
    # Create empty list for each vertex
    adj_list = {i: [] for i in range(NUM_VERTICES)}
    
    # Add neighbors for each edge
    for (i, j, weight) in EDGES:
        adj_list[i].append(j)
        adj_list[j].append(i)  # undirected - add both directions
    
    return adj_list
def build_csr():
    # First build adjacency list to help construct CSR
    adj_list = build_adjacency_list()
    
    # Col array: all neighbors listed vertex by vertex
    col = []
    # Row array: starting position of each vertex in col array
    row = []
    
    current_position = 0
    for i in range(NUM_VERTICES):
        # Record where this vertex's neighbors start
        row.append(current_position)
        # Add all neighbors to col array
        for neighbor in adj_list[i]:
            col.append(neighbor)
            current_position += 1
    
    # Add final position as end marker
    row.append(current_position)
    
    return row, col
def build_edge_list():
    # Edge list is simply our EDGES data
    # Each entry is (vertex_i, vertex_j, weight)
    edge_list = [(i, j) for (i, j, weight) in EDGES]
    return edge_list
def print_all_structures():
    print('=' * 60)
    print('MODULE 1 - STORAGE')
    print('Legacy builders below expose an unweighted topology projection.')
    print('Matrix:', build_adjacency_matrix(), sep=chr(10))
    print('Adjacency list:', build_adjacency_list())
    print('CSR offsets and columns:', build_csr())
    print('Edge pairs:', build_edge_list())
    from graphlab.engine import generate, storage
    report = storage(generate())
    print('Weighted storage comparison (actual numeric buffer bytes):')
    for row in report['rows']:
        print(row['name'], row['payload_bytes'], 'bytes; allocation estimate', row['allocated_bytes_estimate'])
    print(report['method'])

def visualize_graph():
    # Create networkx graph
    G = nx.Graph()
    
    # Add all vertices
    G.add_nodes_from(range(NUM_VERTICES))
    
    # Add all edges with weights
    for (i, j, weight) in EDGES:
        G.add_edge(i, j, weight=weight)
    
    # Create figure
    plt.figure(figsize=(10, 6))
    plt.title("Our Graph - Used Throughout All Modules", 
               fontsize=14, fontweight='bold')
    
    # Draw nodes
    nx.draw_networkx_nodes(G, POSITIONS, 
                           node_color='lightblue',
                           node_size=800)
    
    # Draw edges
    nx.draw_networkx_edges(G, POSITIONS, 
                           edge_color='gray',
                           width=2)
    
    # Draw node labels
    nx.draw_networkx_labels(G, POSITIONS,
                            font_size=12,
                            font_weight='bold')
    
    # Draw edge weight labels
    edge_labels = {(i, j): w for (i, j, w) in EDGES}
    nx.draw_networkx_edge_labels(G, POSITIONS,
                                 edge_labels=edge_labels,
                                 font_size=10)
    
    # Highlight hub vertex (vertex 3)
    nx.draw_networkx_nodes(G, POSITIONS,
                           nodelist=[3],
                           node_color='orange',
                           node_size=800)
    
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('graph_visualization.png', dpi=150)
    plt.show()
    print("Graph saved as graph_visualization.png")
def visualize_memory_comparison():
    # Data for comparison
    structures = ['Adjacency\nMatrix', 'Adjacency\nList', 'CSR', 'Edge List']
    from graphlab.engine import generate, storage
    sizes = [row['payload_bytes'] for row in storage(generate())['rows']]
    colors = ['red', 'orange', 'green', 'blue']

    # Create bar chart
    plt.figure(figsize=(10, 6))
    plt.title("Memory Usage Comparison - All 4 Storage Structures",
              fontsize=14, fontweight='bold')

    bars = plt.bar(structures, sizes, color=colors, alpha=0.7, edgecolor='black')

    # Add value labels on top of each bar
    for bar, size in zip(bars, sizes):
        plt.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.5,
                 str(size) + ' bytes',
                 ha='center', va='bottom',
                 fontweight='bold', fontsize=11)

    plt.ylabel("Weighted numeric payload (bytes)", fontsize=12)
    plt.xlabel("Storage Structure", fontsize=12)
    plt.ylim(0, max(sizes) * 1.2)

    # Add explanation text
    plt.figtext(0.5, 0.01,
                "int64 indices / float64 weights; headers and label strings excluded",
                ha='center', fontsize=10, style='italic')

    plt.tight_layout()
    plt.savefig('memory_comparison.png', dpi=150)
    plt.show()
    print("Memory comparison saved as memory_comparison.png")
def run():
    print_all_structures()
    visualize_graph()
    visualize_memory_comparison()

if __name__ == "__main__":
    run()
    
