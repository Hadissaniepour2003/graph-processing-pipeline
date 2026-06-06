# module3_vertex_partition.py
# Implements FENNEL and Label Propagation vertex partitioning
# Compares both methods on the same graph

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import math
from graph_data import NUM_VERTICES, EDGES, POSITIONS, COMMUNITIES
def build_adjacency_list():
    adj_list = {i: [] for i in range(NUM_VERTICES)}
    for (i, j, weight) in EDGES:
        adj_list[i].append(j)
        adj_list[j].append(i)
    return adj_list
def fennel(num_partitions=2):
    adj_list = build_adjacency_list()
    
    # Calculate alpha parameter
    # alpha = sqrt(k) * |E| / |V|^1.5
    num_edges = len(EDGES)
    alpha = (math.sqrt(num_partitions) * num_edges) / (NUM_VERTICES ** 1.5)
    
    print(f"\nFENNEL Parameters:")
    print(f"   Partitions (k): {num_partitions}")
    print(f"   Alpha: {alpha:.4f}")
    
    # Initialize all vertices as unassigned (-1)
    assignments = {i: -1 for i in range(NUM_VERTICES)}
    partition_sizes = {i: 0 for i in range(num_partitions)}
    
    # Process vertices one by one (streaming)
    for vertex in range(NUM_VERTICES):
        best_partition = 0
        best_score = float('-inf')
        
        for p in range(num_partitions):
            # Term 1: neighbors already in partition p
            neighbors_in_p = sum(
                1 for neighbor in adj_list[vertex]
                if assignments[neighbor] == p
            )
            
            # Term 2: balance penalty
            penalty = alpha * partition_sizes[p]
            
            # Final score
            score = neighbors_in_p - penalty
            
            if score > best_score:
                best_score = score
                best_partition = p
        
        # Assign vertex to best partition
        assignments[vertex] = best_partition
        partition_sizes[best_partition] += 1
        
        print(f"   Vertex {vertex} → Partition {best_partition} "
              f"(score: {best_score:.4f})")
    
    return assignments, partition_sizes
def label_propagation(num_partitions=2):
    adj_list = build_adjacency_list()
    
    # Initialize with random labels (0 or 1)
    import random
    random.seed(42)  # fixed seed for reproducibility
    assignments = {i: random.randint(0, num_partitions-1) 
                  for i in range(NUM_VERTICES)}
    
    print(f"\nLabel Propagation:")
    print(f"   Initial labels: {assignments}")
    
    max_iterations = 100
    for iteration in range(max_iterations):
        changed = False
        new_assignments = assignments.copy()
        
        for vertex in range(NUM_VERTICES):
            # Count neighbor labels
            label_counts = {p: 0 for p in range(num_partitions)}
            for neighbor in adj_list[vertex]:
                label_counts[assignments[neighbor]] += 1
            
            # Adopt majority label
            majority_label = max(label_counts, key=label_counts.get)
            
            # Check for tie - keep current label
            max_count = max(label_counts.values())
            tied_labels = [l for l, c in label_counts.items() 
                          if c == max_count]
            if len(tied_labels) > 1:
                majority_label = assignments[vertex]
            
            if majority_label != assignments[vertex]:
                new_assignments[vertex] = majority_label
                changed = True
        
        assignments = new_assignments
        print(f"   Iteration {iteration + 1}: {assignments}")
        
        # Terminate if nothing changed
        if not changed:
            print(f"   Converged after {iteration + 1} iterations!")
            break
    
    # Calculate partition sizes
    partition_sizes = {p: sum(1 for v in assignments.values() if v == p)
                      for p in range(num_partitions)}
    
    return assignments, partition_sizes
def evaluate_partition(assignments, num_partitions=2):
    adj_list = build_adjacency_list()
    
    # Count cut edges
    cut_edges = 0
    for (i, j, weight) in EDGES:
        if assignments[i] != assignments[j]:
            cut_edges += 1
    
    # Calculate balance
    partition_sizes = {p: sum(1 for v in assignments.values() if v == p)
                      for p in range(num_partitions)}
    
    ideal_size = NUM_VERTICES / num_partitions
    imbalance = max(abs(size - ideal_size) 
                   for size in partition_sizes.values())
    
    return cut_edges, partition_sizes, imbalance
def print_results():
    print("=" * 60)
    print("MODULE 3 - VERTEX PARTITIONING")
    print("=" * 60)

    # Run FENNEL
    print("\nRunning FENNEL...")
    fennel_assignments, fennel_sizes = fennel(num_partitions=2)
    fennel_cuts, fennel_partition_sizes, fennel_imbalance = evaluate_partition(
        fennel_assignments)

    print(f"\nFENNEL Results:")
    print(f"   Assignments: {fennel_assignments}")
    print(f"   Partition sizes: {fennel_partition_sizes}")
    print(f"   Cut edges: {fennel_cuts}")
    print(f"   Imbalance: {fennel_imbalance}")

    # Run Label Propagation
    print("\nRunning Label Propagation...")
    lp_assignments, lp_sizes = label_propagation(num_partitions=2)
    lp_cuts, lp_partition_sizes, lp_imbalance = evaluate_partition(
        lp_assignments)

    print(f"\nLabel Propagation Results:")
    print(f"   Assignments: {lp_assignments}")
    print(f"   Partition sizes: {lp_partition_sizes}")
    print(f"   Cut edges: {lp_cuts}")
    print(f"   Imbalance: {lp_imbalance}")

    # Comparison
    print("\n" + "=" * 60)
    print("COMPARISON:")
    print(f"{'Metric':<20} {'FENNEL':<15} {'Label Propagation':<15}")
    print(f"{'Cut Edges':<20} {fennel_cuts:<15} {lp_cuts:<15}")
    print(f"{'Imbalance':<20} {fennel_imbalance:<15} {lp_imbalance:<15}")
    print(f"{'P0 size':<20} {fennel_partition_sizes[0]:<15} {lp_partition_sizes[0]:<15}")
    print(f"{'P1 size':<20} {fennel_partition_sizes[1]:<15} {lp_partition_sizes[1]:<15}")
    print("=" * 60)

    return fennel_assignments, lp_assignments
def visualize_partitions(fennel_assignments, lp_assignments):
    G = nx.Graph()
    G.add_nodes_from(range(NUM_VERTICES))
    for (i, j, weight) in EDGES:
        G.add_edge(i, j, weight=weight)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Module 3 - Vertex Partitioning Comparison",
                 fontsize=14, fontweight='bold')

    # Color maps for partitions
    colors_map = {0: 'lightblue', 1: 'lightcoral'}

    # Plot 1 - Ground Truth
    ax1 = axes[0]
    ax1.set_title("Ground Truth Communities")
    community_colors = ['lightblue' if COMMUNITIES[v] == 'A' 
                       else 'lightcoral' 
                       for v in range(NUM_VERTICES)]
    nx.draw_networkx_nodes(G, POSITIONS, node_color=community_colors,
                           node_size=800, ax=ax1)
    nx.draw_networkx_edges(G, POSITIONS, edge_color='gray',
                           width=2, ax=ax1)
    nx.draw_networkx_labels(G, POSITIONS, font_size=12,
                            font_weight='bold', ax=ax1)
    ax1.set_title("Ground Truth\n(Community A=blue, B=red)")
    ax1.axis('off')

    # Plot 2 - FENNEL
    ax2 = axes[1]
    fennel_colors = [colors_map[fennel_assignments[v]] 
                    for v in range(NUM_VERTICES)]
    nx.draw_networkx_nodes(G, POSITIONS, node_color=fennel_colors,
                           node_size=800, ax=ax2)
    nx.draw_networkx_edges(G, POSITIONS, edge_color='gray',
                           width=2, ax=ax2)
    nx.draw_networkx_labels(G, POSITIONS, font_size=12,
                            font_weight='bold', ax=ax2)
    
    # Highlight cut edges in red
    cut_edges_fennel = [(i, j) for (i, j, w) in EDGES 
                        if fennel_assignments[i] != fennel_assignments[j]]
    nx.draw_networkx_edges(G, POSITIONS, edgelist=cut_edges_fennel,
                           edge_color='red', width=3, ax=ax2)
    
    fennel_cuts = len(cut_edges_fennel)
    ax2.set_title(f"FENNEL\n(Cut edges: {fennel_cuts} shown in red)")
    ax2.axis('off')

    # Plot 3 - Label Propagation
    ax3 = axes[2]
    lp_colors = [colors_map[lp_assignments[v]] 
                for v in range(NUM_VERTICES)]
    nx.draw_networkx_nodes(G, POSITIONS, node_color=lp_colors,
                           node_size=800, ax=ax3)
    nx.draw_networkx_edges(G, POSITIONS, edge_color='gray',
                           width=2, ax=ax3)
    nx.draw_networkx_labels(G, POSITIONS, font_size=12,
                            font_weight='bold', ax=ax3)
    
    # Highlight cut edges in red
    cut_edges_lp = [(i, j) for (i, j, w) in EDGES 
                    if lp_assignments[i] != lp_assignments[j]]
    nx.draw_networkx_edges(G, POSITIONS, edgelist=cut_edges_lp,
                           edge_color='red', width=3, ax=ax3)
    
    lp_cuts = len(cut_edges_lp)
    ax3.set_title(f"Label Propagation\n(Cut edges: {lp_cuts} shown in red)")
    ax3.axis('off')

    plt.tight_layout()
    plt.savefig('vertex_partitioning.png', dpi=150)
    plt.show()
    print("Vertex partitioning saved as vertex_partitioning.png")
def run():
    fennel_assignments, lp_assignments = print_results()
    visualize_partitions(fennel_assignments, lp_assignments)

if __name__ == "__main__":
    run()