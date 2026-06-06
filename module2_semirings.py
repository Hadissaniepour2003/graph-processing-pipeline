# module2_semirings.py
# Implements all 3 semirings and computes matrix powers
# Standard (count paths), Any-Pair (path exists?), Min-Plus (shortest path)

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from graph_data import NUM_VERTICES, EDGES, POSITIONS
def build_weighted_matrix():
    # Initialize with infinity (no connection)
    INF = float('inf')
    matrix = np.full((NUM_VERTICES, NUM_VERTICES), INF)
    
    # Distance from vertex to itself is 0
    for i in range(NUM_VERTICES):
        matrix[i][i] = 0
    
    # Fill in actual edge weights
    for (i, j, weight) in EDGES:
        matrix[i][j] = weight
        matrix[j][i] = weight  # undirected
    
    return matrix

def build_unweighted_matrix():
    # Initialize with zeros
    matrix = np.zeros((NUM_VERTICES, NUM_VERTICES), dtype=int)
    
    # Fill in 1 where edge exists
    for (i, j, weight) in EDGES:
        matrix[i][j] = 1
        matrix[j][i] = 1  # undirected
    
    return matrix
def standard_multiply(A, B):
    n = len(A)
    C = np.zeros((n, n), dtype=int)
    
    for i in range(n):
        for j in range(n):
            total = 0
            for k in range(n):
                # Standard semiring: multiply then add
                total += A[i][k] * B[k][j]
            C[i][j] = total
    
    return C

def standard_power(A, power):
    result = A.copy()
    for _ in range(power - 1):
        result = standard_multiply(result, A)
    return result
def anypair_multiply(A, B):
    n = len(A)
    C = np.zeros((n, n), dtype=bool)
    
    for i in range(n):
        for j in range(n):
            exists = False
            for k in range(n):
                # Any-Pair semiring: AND then OR
                if A[i][k] and B[k][j]:
                    exists = True
                    break
            C[i][j] = exists
    
    return C

def anypair_power(A, power):
    # Convert to boolean matrix
    A_bool = A.astype(bool)
    result = A_bool.copy()
    for _ in range(power - 1):
        result = anypair_multiply(result, A_bool)
    return result
def minplus_multiply(A, B):
    n = len(A)
    INF = float('inf')
    C = np.full((n, n), INF)
    
    for i in range(n):
        for j in range(n):
            minimum = INF
            for k in range(n):
                # Min-Plus semiring: add then minimize
                if A[i][k] + B[k][j] < minimum:
                    minimum = A[i][k] + B[k][j]
            C[i][j] = minimum
    
    return C

def minplus_power(A, power):
    result = A.copy()
    for _ in range(power - 1):
        result = minplus_multiply(result, A)
    return result
def print_results():
    print("=" * 60)
    print("MODULE 2 - SEMIRING MATRIX MULTIPLICATION")
    print("=" * 60)

    # Standard Semiring
    A_unweighted = build_unweighted_matrix()
    print("\nSTANDARD SEMIRING (count paths):")
    print("A^1 (direct connections):")
    print(A_unweighted)
    A2_standard = standard_power(A_unweighted, 2)
    print("\nA^2 (paths of exactly 2 hops):")
    print(A2_standard)
    A3_standard = standard_power(A_unweighted, 3)
    print("\nA^3 (paths of exactly 3 hops):")
    print(A3_standard)

    # Any-Pair Semiring
    print("\n" + "=" * 60)
    print("ANY-PAIR SEMIRING (path exists?):")
    A2_anypair = anypair_power(A_unweighted, 2)
    print("\nA^2 (does 2-hop path exist?):")
    print(A2_anypair.astype(int))
    A3_anypair = anypair_power(A_unweighted, 3)
    print("\nA^3 (does 3-hop path exist?):")
    print(A3_anypair.astype(int))

    # Min-Plus Semiring
    print("\n" + "=" * 60)
    print("MIN-PLUS SEMIRING (shortest path):")
    A_weighted = build_weighted_matrix()
    print("\nA^1 (direct edge weights):")
    print(A_weighted)
    A2_minplus = minplus_power(A_weighted, 2)
    print("\nA^2 (shortest 2-hop path costs):")
    print(A2_minplus)
    A3_minplus = minplus_power(A_weighted, 3)
    print("\nA^3 (shortest 3-hop path costs):")
    print(A3_minplus)
    print("\nWhen A^n = A^(n-1), all shortest paths found!")
    print("=" * 60)
def visualize_shortest_paths():
    # Compute shortest paths using Min-Plus
    A_weighted = build_weighted_matrix()
    
    # Keep multiplying until matrix stops changing
    current = A_weighted.copy()
    for _ in range(NUM_VERTICES):
        next_matrix = minplus_multiply(current, A_weighted)
        if np.array_equal(current, next_matrix):
            break
        current = next_matrix
    
    shortest_paths = current

    # Create networkx graph
    G = nx.Graph()
    G.add_nodes_from(range(NUM_VERTICES))
    for (i, j, weight) in EDGES:
        G.add_edge(i, j, weight=weight)

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("Module 2 - Min-Plus Semiring: Shortest Paths",
                 fontsize=14, fontweight='bold')

    # Left plot - original graph
    ax1.set_title("Original Graph with Edge Weights")
    nx.draw_networkx_nodes(G, POSITIONS, node_color='lightblue',
                           node_size=800, ax=ax1)
    nx.draw_networkx_edges(G, POSITIONS, edge_color='gray',
                           width=2, ax=ax1)
    nx.draw_networkx_labels(G, POSITIONS, font_size=12,
                            font_weight='bold', ax=ax1)
    edge_labels = {(i, j): w for (i, j, w) in EDGES}
    nx.draw_networkx_edge_labels(G, POSITIONS,
                                 edge_labels=edge_labels,
                                 font_size=10, ax=ax1)
    nx.draw_networkx_nodes(G, POSITIONS, nodelist=[3],
                           node_color='orange', node_size=800, ax=ax1)
    ax1.axis('off')

    # Right plot - shortest path matrix as heatmap
    ax2.set_title("Shortest Path Distances Between All Vertices")
    
    # Replace infinity with -1 for display
    display_matrix = shortest_paths.copy()
    display_matrix[display_matrix == float('inf')] = -1
    
    im = ax2.imshow(display_matrix, cmap='YlOrRd')
    plt.colorbar(im, ax=ax2)
    
    # Add text annotations
    for i in range(NUM_VERTICES):
        for j in range(NUM_VERTICES):
            value = shortest_paths[i][j]
            text = str(int(value)) if value != float('inf') else '∞'
            ax2.text(j, i, text, ha='center', va='center',
                    fontsize=10, fontweight='bold')
    
    ax2.set_xticks(range(NUM_VERTICES))
    ax2.set_yticks(range(NUM_VERTICES))
    ax2.set_xlabel("Destination Vertex")
    ax2.set_ylabel("Source Vertex")

    plt.tight_layout()
    plt.savefig('shortest_paths.png', dpi=150)
    plt.show()
    print("Shortest paths saved as shortest_paths.png")
def run():
    print_results()
    visualize_shortest_paths()

if __name__ == "__main__":
    run()