import argparse
import json
import sys
import os
from shexer.shaper import Shaper

def extract_shape(shape_output_path):

    try:        
        entity_id = "Q1248784"  # Example entity
        shape_map_raw = f"<http://www.wikidata.org/entity/{entity_id}>@<http://www.wikidata.org/prop/direct/P31>"  # Example shape

        namespaces_dict = {
            "http://example.org/": "ex",
            "http://www.w3.org/XML/1998/namespace/": "xml",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
            "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
            "http://www.w3.org/2001/XMLSchema#": "xsd",
            "http://xmlns.com/foaf/0.1/": "foaf",
            "http://www.wikidata.org/prop/direct/" : "wdt",
            "http://www.wikidata.org/entity/" : "wd"
            }

        namespaces_to_ignore = [
            "http://www.wikidata.org/prop/",
            "http://www.w3.org/2004/02/skos/core#",
            "http://schema.org/",
            "http://wikiba.se/ontology#",
            "http://www.wikidata.org/prop/direct-normalized/"
        ]

        shaper = Shaper(
            shape_map_raw=shape_map_raw,
            url_endpoint="https://query.wikidata.org/sparql",
            namespaces_dict=namespaces_dict,
            disable_comments=True,
            namespaces_to_ignore=namespaces_to_ignore,
            wikidata_annotation=True,
            track_classes_for_entities_at_last_depth_level=True,
            depth_for_building_subgraph=2
        )

        str_result = shaper.shex_graph(string_output=True)

        # Ensure output directory exists
        os.makedirs(shape_output_path, exist_ok=True)

        # Generate a filename dynamically
        shape_output_path = os.path.join(shape_output_path, f"{entity_id}_shape.shex")

        # Save the extracted shape to the generated path
        with open(shape_output_path, "w", encoding="utf-8") as f:
            f.write(str_result)


    except Exception as e:
        print(f"Error during shape extraction: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="Extract schema from Wikidata and save it to a file.")
    parser.add_argument("--shape-output-path", type=str, required=True, help="Path to save the extracted shape.")
    
    args = parser.parse_args()
    
    exit_code = extract_shape(args.shape_output_path)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()