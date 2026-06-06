# main.py
# Graph Processing Pipeline
# Demonstrates graph storage, semirings, and partitioning
# University of Bayreuth - Graph Processing & Machine Learning

import module1_storage
import module2_semirings
import module3_vertex_partition
import module4_edge_partition

def main():
    print("\n" + "=" * 60)
    print("   GRAPH PROCESSING PIPELINE")
    print("   University of Bayreuth")
    print("   Graph Processing & Machine Learning")
    print("=" * 60)

    print("\n>>> MODULE 1: GRAPH STORAGE STRUCTURES")
    print("Comparing adjacency matrix, list, CSR and edge list")
    module1_storage.run()

    print("\n>>> MODULE 2: SEMIRING MATRIX MULTIPLICATION")
    print("Standard, Any-Pair and Min-Plus semirings")
    module2_semirings.run()

    print("\n>>> MODULE 3: VERTEX PARTITIONING")
    print("Comparing FENNEL and Label Propagation")
    module3_vertex_partition.run()

    print("\n>>> MODULE 4: EDGE PARTITIONING")
    print("Comparing DBH and HDRF algorithms")
    module4_edge_partition.run()

    print("\n" + "=" * 60)
    print("   PIPELINE COMPLETE")
    print("   Check generated PNG files for all visualizations")
    print("=" * 60)

if __name__ == "__main__":
    main()