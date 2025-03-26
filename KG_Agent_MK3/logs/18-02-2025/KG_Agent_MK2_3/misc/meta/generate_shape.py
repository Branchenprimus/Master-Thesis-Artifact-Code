#!/usr/bin/env python3
"""
validate_shexer_params.py

Validates each line in an ND-JSON file containing Shexer parameters
by attempting to instantiate a Shaper and run a quick shape extraction.
If successful, saves the resulting ShEx shapes to a specified directory.
"""

import argparse
import json
import sys
import logging
import os

from shexer.shaper import Shaper
from shexer.consts import NT, SHEXC

def main():
    parser = argparse.ArgumentParser(
        description="Validate Shexer configurations from an ND-JSON file and save shapes if valid."
    )
    parser.add_argument(
        "--shexer_params_path",
        required=True,
        help="Path to ND-JSON file containing Shexer parameter objects (one per line)."
    )
    parser.add_argument(
        "--shape_output_dir",
        required=True,
        help="Directory in which each successful configuration's shape is saved."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    ndjson_path = args.shexer_params_path
    output_dir = args.shape_output_dir

    # Ensure output directory exists (create if necessary)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create or access output directory {output_dir}: {e}")
        sys.exit(1)

    # Read ND-JSON file
    try:
        with open(ndjson_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        logging.error(f"Failed to read ND-JSON file {ndjson_path}: {e}")
        sys.exit(1)

    total = len(lines)
    logging.info(f"Loaded {total} lines from {ndjson_path}.")

    success_count = 0
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            logging.warning(f"Line {idx} is empty or whitespace. Skipping.")
            continue

        # Parse the JSON
        try:
            config = json.loads(line)
        except json.JSONDecodeError as e:
            logging.error(f"Line {idx}: invalid JSON - {e}")
            continue

        # Basic mapping from ND-JSON config to Shaper() kwargs. 
        # Adjust as needed if your config has additional or different fields.
        shaper_kwargs = {}

        if "graph_file_input" in config:
            shaper_kwargs["graph_file_input"] = config["graph_file_input"]
        if "input_format" in config:
            shaper_kwargs["input_format"] = config["input_format"]
        if "target_classes" in config:
            shaper_kwargs["target_classes"] = config["target_classes"]
        if "all_classes_mode" in config:
            shaper_kwargs["all_classes_mode"] = config["all_classes_mode"]
        if "shape_map_raw" in config:
            shaper_kwargs["shape_map_raw"] = config["shape_map_raw"]

        if "instances_cap" in config:
            shaper_kwargs["instances_cap"] = config["instances_cap"]
        if "depth_for_building_subgraph" in config:
            shaper_kwargs["depth_for_building_subgraph"] = config["depth_for_building_subgraph"]

        # Instantiate a Shaper and do a quick shape extraction
        try:
            shaper = Shaper(**shaper_kwargs)
            shape_output = shaper.shex_graph(string_output=True, output_format=SHEXC)

            logging.info(f"Line {idx}: Validation successful.")
            success_count += 1

            # Save shape to a file in the output directory
            shape_filename = f"shapes_line_{idx}.shex"
            shape_path = os.path.join(output_dir, shape_filename)
            try:
                with open(shape_path, "w", encoding="utf-8") as shape_file:
                    shape_file.write(shape_output)
                logging.info(f"Saved shapes to {shape_path}")
            except Exception as e:
                logging.error(f"Failed to write shape file for line {idx}: {e}")

        except Exception as e:
            logging.error(f"Line {idx}: Shexer validation failed - {e}")

    logging.info(f"Validation complete. {success_count}/{total} lines succeeded.")
    if success_count == total:
        sys.exit(0)
    else:
        # Exit with 1 if any line failed
        sys.exit(1)

if __name__ == "__main__":
    main()
