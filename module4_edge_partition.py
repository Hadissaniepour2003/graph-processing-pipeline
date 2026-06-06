# module4_edge_partition.py
# Implements DBH and HDRF edge partitioning algorithms
# Compares replication factors on a power-law inspired graph

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import math
from graph_data import NUM_VERTICES, EDGES, POSITIONS
def calculate_degrees():
    degrees = {i: 0 for i in range(NUM_VERTICES)}
    for (i, j, weight) in EDGES:
        degrees[i] += 1
        degrees[j] += 1
    return degrees
def dbh(num_partitions=2):
    degrees = calculate_degrees()
    
    # Track which edges go to which partition
    partition_edges = {p: [] for p in range(num_partitions)}
    # Track which vertices appear on which partitions
    vertex_partitions = {i: set() for i in range(NUM_VERTICES)}
    
    print(f"\nDBH (Degree-Based Hashing):")
    print(f"   Partitions: {num_partitions}")
    
    for (i, j, weight) in EDGES:
        # Hash based on LOWER degree vertex
        if degrees[i] < degrees[j]:
            partition = hash(i) % num_partitions
            hash_vertex = i
        else:
            partition = hash(j) % num_partitions
            hash_vertex = j
        
        # Assign edge to partition
        partition_edges[partition].append((i, j))
        
        # Both vertices now exist on this partition
        vertex_partitions[i].add(partition)
        vertex_partitions[j].add(partition)
        
        print(f"   Edge ({i},{j}) → Partition {partition} "
              f"[hashed on vertex {hash_vertex} "
              f"degree={degrees[hash_vertex]}]")
    
    return partition_edges, vertex_partitions
def hdrf(num_partitions=2, lambda_balance=1.1, epsilon=1.0):
    degrees = calculate_degrees()
    
    # Track partition state
    partition_edges = {p: [] for p in range(num_partitions)}
    vertex_partitions = {i: set() for i in range(NUM_VERTICES)}
    partition_sizes = {p: 0 for p in range(num_partitions)}
    
    print(f"\nHDRF (High Degree Replicated First):")
    print(f"   Partitions: {num_partitions}")
    print(f"   Lambda: {lambda_balance}")
    
    for (i, j, weight) in EDGES:
        best_partition = 0
        best_score = float('-inf')
        
        # Calculate theta (degree weights)
        total_degree = degrees[i] + degrees[j]
        theta_i = degrees[i] / total_degree
        theta_j = degrees[j] / total_degree
        
        # Score each partition
        maxsize = max(partition_sizes.values())
        minsize = min(partition_sizes.values())
        
        for p in range(num_partitions):
            # Replication score for vertex i
            if p in vertex_partitions[i]:
                g_i = 1 + (1 - theta_i)
            else:
                g_i = 0
            
            # Replication score for vertex j
            if p in vertex_partitions[j]:
                g_j = 1 + (1 - theta_j)
            else:
                g_j = 0
            
            # Replication term
            c_rep = g_i + g_j
            
            # Balance term
            if maxsize == minsize:
                c_bal = 0
            else:
                c_bal = lambda_balance * (
                    (maxsize - partition_sizes[p]) /
                    (epsilon + maxsize - minsize)
                )
            
            score = c_rep + c_bal
            
            if score > best_score:
                best_score = score
                best_partition = p
        
        # Assign edge to best partition
        partition_edges[best_partition].append((i, j))
        vertex_partitions[i].add(best_partition)
        vertex_partitions[j].add(best_partition)
        partition_sizes[best_partition] += 1
        print(f"   Edge ({i},{j}) → Partition {best_partition} "
              f"(score: {best_score:.4f})")
    
    return partition_edges, vertex_partitions
        
     
def calculate_replication_factor(vertex_partitions):
    # Sum of all vertex appearances across all partitions
    total_appearances = sum(
        len(partitions) for partitions in vertex_partitions.values()
    )
    # RF = total appearances / number of vertices
    rf = total_appearances / NUM_VERTICES
    return rf

def print_replication_details(vertex_partitions, algorithm_name):
    print(f"\n{algorithm_name} Replication Details:")
    for vertex, partitions in vertex_partitions.items():
        if len(partitions) > 1:
            print(f"   Vertex {vertex} REPLICATED on partitions {partitions} "
                  f"← {len(partitions)} copies")
        else:
            print(f"   Vertex {vertex} on partition {partitions}")
    rf = calculate_replication_factor(vertex_partitions)
    print(f"   Replication Factor: {rf:.4f}")
    return rf
def print_results():
    print("=" * 60)
    print("MODULE 4 - EDGE PARTITIONING")
    print("=" * 60)

    # Run DBH
    dbh_partition_edges, dbh_vertex_partitions = dbh(num_partitions=2)
    dbh_rf = print_replication_details(dbh_vertex_partitions, "DBH")

    # Run HDRF
    hdrf_partition_edges, hdrf_vertex_partitions = hdrf(num_partitions=2)
    hdrf_rf = print_replication_details(hdrf_vertex_partitions, "HDRF")

    # Comparison
    print("\n" + "=" * 60)
    print("COMPARISON:")
    print(f"{'Metric':<25} {'DBH':<15} {'HDRF':<15}")
    print(f"{'Replication Factor':<25} {dbh_rf:<15.4f} {hdrf_rf:<15.4f}")
    
    dbh_p0 = len(dbh_partition_edges[0])
    dbh_p1 = len(dbh_partition_edges[1])
    hdrf_p0 = len(hdrf_partition_edges[0])
    hdrf_p1 = len(hdrf_partition_edges[1])
    
    print(f"{'Edges in P0':<25} {dbh_p0:<15} {hdrf_p0:<15}")
    print(f"{'Edges in P1':<25} {dbh_p1:<15} {hdrf_p1:<15}")
    print(f"{'Winner':<25} {'HDRF wins if RF lower':>15}")
    print("=" * 60)

    return (dbh_partition_edges, dbh_vertex_partitions,
            hdrf_partition_edges, hdrf_vertex_partitions)
def visualize_edge_partitioning(dbh_partition_edges, dbh_vertex_partitions,
                                 hdrf_partition_edges, hdrf_vertex_partitions):
    G = nx.Graph()
    G.add_nodes_from(range(NUM_VERTICES))
    for (i, j, weight) in EDGES:
        G.add_edge(i, j)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle("Module 4 - Edge Partitioning Comparison",
                 fontsize=14, fontweight='bold')

    edge_colors_map = {0: 'blue', 1: 'red'}

    for ax, partition_edges, vertex_partitions, title in [
        (axes[0], dbh_partition_edges, dbh_vertex_partitions, "DBH"),
        (axes[1], hdrf_partition_edges, hdrf_vertex_partitions, "HDRF")
    ]:
        # Node colors based on replication
        node_colors = []
        for v in range(NUM_VERTICES):
            if len(vertex_partitions[v]) > 1:
                node_colors.append('yellow')  # replicated
            elif 0 in vertex_partitions[v]:
                node_colors.append('lightblue')  # partition 0
            else:
                node_colors.append('lightcoral')  # partition 1

        nx.draw_networkx_nodes(G, POSITIONS, node_color=node_colors,
                               node_size=800, ax=ax)
        nx.draw_networkx_labels(G, POSITIONS, font_size=12,
                                font_weight='bold', ax=ax)

        # Draw edges colored by partition
        for p, edges in partition_edges.items():
            nx.draw_networkx_edges(G, POSITIONS,
                                   edgelist=edges,
                                   edge_color=edge_colors_map[p],
                                   width=3, ax=ax,
                                   label=f'Partition {p}')

        # Calculate RF for title
        rf = calculate_replication_factor(vertex_partitions)
        replicated = sum(1 for v in vertex_partitions.values()
                        if len(v) > 1)

        ax.set_title(f"{title}\nRF={rf:.4f} | "
                    f"Blue=P0 | Red=P1 | Yellow=Replicated\n"
                    f"Replicated vertices: {replicated}")
        ax.axis('off')

    plt.tight_layout()
    plt.savefig('edge_partitioning.png', dpi=150)
    plt.show()
    print("Edge partitioning saved as edge_partitioning.png") 
def run():
    results = print_results()
    visualize_edge_partitioning(*results)

if __name__ == "__main__":
    run()