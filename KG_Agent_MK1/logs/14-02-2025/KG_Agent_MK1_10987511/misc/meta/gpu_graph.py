#!/usr/bin/py
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

def clean_csv(csv_file):
    """ Cleans up CSV file by removing repeated headers and extra spaces. """
    clean_lines = []
    with open(csv_file, "r") as f:
        for line in f:
            if not line.startswith("timestamp, index"):  # Remove repeated headers
                clean_lines.append(line)
    
    with open(csv_file, "w") as f:
        f.writelines(clean_lines)

def visualize_gpu_usage(csv_file, output_image):
    """ Reads GPU usage log from CSV and generates a visualization. """
    try:
        # Clean up CSV file before reading
        clean_csv(csv_file)

        # Read the cleaned CSV file
        data = pd.read_csv(csv_file, skip_blank_lines=True)

        # Rename columns to remove spaces
        data.columns = [col.strip() for col in data.columns]

        # Convert timestamp to datetime
        data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")

        # Convert GPU utilization to numeric (handle percentage sign)
        data["utilization.gpu [%]"] = data["utilization.gpu [%]"].str.replace(" %", "").astype(float)

        # Extract unique GPU indices
        gpu_indices = data["index"].unique()

        plt.figure(figsize=(12, 5))
        for gpu_index in gpu_indices:
            gpu_data = data[data["index"] == gpu_index]
            plt.plot(gpu_data["timestamp"], gpu_data["utilization.gpu [%]"], label=f"GPU {gpu_index}")

        plt.xlabel("Time")
        plt.ylabel("GPU Utilization (%)")
        plt.title("GPU Utilization Over Time")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)

        os.makedirs(os.path.dirname(output_image), exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_image)
        print(f"GPU usage visualization saved to: {output_image}")

    except Exception as e:
        print(f"Error processing the GPU log: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize GPU usage from NVIDIA SMI logs.")
    parser.add_argument("--csv_file", type=str, required=True, help="Path to GPU log CSV file")
    parser.add_argument("--output_image", type=str, required=True, help="Path to save the GPU usage plot")

    args = parser.parse_args()
    visualize_gpu_usage(args.csv_file, args.output_image)
