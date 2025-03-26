import argparse
import json
import os
from shexer.shaper import Shaper

def extract_shape(entity_id, named_entity):
    """
    Extracts the ShEx shape for a given entity from Wikidata.
    """
    try:
        # Format named entity: replace spaces with underscores for consistency
        named_entity_formatted = named_entity.replace(" ", "_")  

        # Define shape map including named entity
        shape_map_raw = f"<http://www.wikidata.org/entity/{entity_id}>@<{named_entity_formatted}>"

        namespaces_dict = {
            "http://example.org/": "ex",
            "http://www.w3.org/XML/1998/namespace/": "xml",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
            "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
            "http://www.w3.org/2001/XMLSchema#": "xsd",
            "http://xmlns.com/foaf/0.1/": "foaf",
            "http://www.wikidata.org/prop/direct/": "wdt",
            "http://www.wikidata.org/entity/": "wd"
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

        return shaper.shex_graph(string_output=True)

    except Exception as e:
        print(f"Error extracting shape for {entity_id}: {e}")
        return ""

def process_json(json_file, shape_output_path):
    """
    Processes the JSON file and generates ShEx files for each entity in each question-answer pair.
    """
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    for idx, entry in enumerate(data):
        # Extract named entities from LLM (list of names)
        named_entities = entry.get("llm_extracted_entity_names", [])

        # Extract entity mappings from Wikidata resolution (dictionary)
        entity_dict = entry.get("wikidata_entities_resolved", {})

        if not named_entities or not entity_dict:
            print(f"⚠️ Warning: Skipping pair {idx} due to missing entity data.")
            continue  # Skip if data is incomplete

        combined_shex = ""  # Store all shapes for the pair

        # Iterate over named entities and retrieve their corresponding Q-IDs
        for named_entity in named_entities:
            entity_id = entity_dict.get(named_entity, None)  # Get Q-ID for entity name

            if entity_id:
                shape = extract_shape(entity_id, named_entity)
                if shape:
                    combined_shex += shape + "\n\n"  # Append each entity's shape

        # Save combined shape to file
        if combined_shex:
            os.makedirs(shape_output_path, exist_ok=True)
            filename = f"pair_{idx}_shape.shex"
            output_filepath = os.path.join(shape_output_path, filename)

            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(combined_shex)

            print(f"✅ Saved combined ShEx shape for {list(entity_dict.values())} to {output_filepath}")

def main():
    parser = argparse.ArgumentParser(description="Extract ShEx schemas from Wikidata entities found in a JSON dataset.")
    parser.add_argument("--json-file", type=str, required=True, help="Path to the JSON file containing extracted entities.")
    parser.add_argument("--shape-output-path", type=str, required=True, help="Path to save the extracted shapes.")

    args = parser.parse_args()
    
    process_json(args.json_file, args.shape_output_path)

if __name__ == "__main__":
    main()
