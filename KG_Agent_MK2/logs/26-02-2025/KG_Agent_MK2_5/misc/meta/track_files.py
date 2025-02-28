#!/usr/bin/env python3
import argparse
import os
import shutil
from datetime import datetime

def copy_files_to_log(root_dir, log_dir):
    """
    Copy all files in the specified root directory to the log directory.
    
    Args:
        root_dir (str): Path of the directory to track files from
        log_dir (str): Path to the log directory where files should be copied
    """
    # Ensure absolute paths
    root_dir = os.path.abspath(root_dir)
    log_dir = os.path.abspath(log_dir)

    # Check if root directory exists
    if not os.path.isdir(root_dir):
        print(f"ERROR: Root directory '{root_dir}' does not exist.")
        return

    # List all files in the specified root directory (non-recursive)
    source_files = [
        os.path.join(root_dir, f) for f in os.listdir(root_dir) if os.path.isfile(os.path.join(root_dir, f))
    ]

    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Create timestamp for logging
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Copy each file
    for source_path in source_files:
        try:
            filename = os.path.basename(source_path)
            dest_path = os.path.join(log_dir, filename)

            shutil.copy2(source_path, dest_path)
            print(f"Successfully copied {filename} to {dest_path}")

        except Exception as e:
            print(f"Error copying {source_path}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Copy all files in the specified directory to a log directory")
    parser.add_argument("--root-dir", required=True, help="Path to the directory containing files to track")
    parser.add_argument("--output", required=True, help="Path to the output log directory")
    args = parser.parse_args()

    copy_files_to_log(args.root_dir, args.output)

if __name__ == "__main__":
    main()
