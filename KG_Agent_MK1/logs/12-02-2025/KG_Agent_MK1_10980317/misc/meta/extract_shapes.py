import argparse
import os
import sys
import rdflib
from shexer.shaper import Shaper
from shexer.consts import TURTLE, SHACL_TURTLE

def validate_paths(turtle_input_path, output_dir, base_filename):
    """Validate input and output paths before execution."""
    
    # Check if input file exists
    if not os.path.exists(turtle_input_path):
        sys.stderr.write(f"❌ ERROR: Turtle input file not found: {turtle_input_path}\n")
        sys.exit(1)

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define output file paths
    shex_output_path = os.path.join(output_dir, f"{base_filename}.shex")
    shacl_output_path = os.path.join(output_dir, f"{base_filename}_shacl.ttl")


    if os.path.exists(shex_output_path) or os.path.exists(shacl_output_path):
        sys.stderr.write(f"❌ ERROR: Output file already exists: {shex_output_path if os.path.exists(shex_output_path) else shacl_output_path}\n")
        sys.exit(1)

    return shex_output_path, shacl_output_path

def extract_classes_from_ttl(turtle_input_path, target_classes_file):
    """Extract all unique RDF classes (rdf:type) from an unknown `.ttl` file."""
    classes = set()
    
    try:
        # Load RDF data
        graph = rdflib.Graph()
        graph.parse(turtle_input_path, format="turtle")

        # Extract all unique rdf:type classes
        for _, _, obj in graph.triples((None, rdflib.RDF.type, None)):
            classes.add(str(obj))  # Convert to string

        if not classes:
            sys.stderr.write("WARNING: No classes found in RDF file. Using an empty target class list.\n")

    except Exception as e:
        sys.stderr.write(f"❌ ERROR: Failed to extract classes from RDF: {e}\n")
        sys.exit(1)

    # Save extracted classes to a file
    with open(target_classes_file, "w", encoding="utf-8") as f:
        for cls in classes:
            f.write(cls + "\n")

def main():
    """Main function to extract ShEx/SHACL from an unknown RDF graph."""
    
    # Command-line arguments
    parser = argparse.ArgumentParser(description="Extract ShEx and SHACL from a Turtle RDF graph.")
    parser.add_argument("--turtle_input_path", required=True, help="Path to turtle input file")
    parser.add_argument("--shape_output_path", required=True, help="Directory where output files will be saved")
    args = parser.parse_args()

    base_filename = os.path.splitext(os.path.basename(args.turtle_input_path))[0]  # Remove .ttl extension

    # Validate paths
    shex_output_path, shacl_output_path = validate_paths(args.turtle_input_path, args.shape_output_path, base_filename)

    # Define a file for dynamically extracted target classes
    target_classes_file = os.path.join(args.shape_output_path, f"{base_filename}_target_classes.txt")

    # Extract classes dynamically from RDF
    extract_classes_from_ttl(args.turtle_input_path, target_classes_file)

    # Initialize SheXer Shaper
    shaper = Shaper(
        graph_file_input=args.turtle_input_path,  # Process any `.ttl` RDF file
        input_format=TURTLE,
        file_target_classes=target_classes_file  # Dynamically extracted classes
    )

    # Generate ShEx
    shaper.shex_graph(output_file=shex_output_path, acceptance_threshold=0.1)
    print(f"✅ ShEx schema written to {shex_output_path}")

    # Generate SHACL
    shaper.shex_graph(output_file=shacl_output_path, acceptance_threshold=0.1, output_format=SHACL_TURTLE)
    print(f"✅ SHACL schema written to {shacl_output_path}")

if __name__ == "__main__":
    main()
