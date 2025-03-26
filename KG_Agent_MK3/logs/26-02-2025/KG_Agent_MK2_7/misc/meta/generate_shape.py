import argparse
import json
import os
import re
from shexer.shaper import Shaper

def clean_shape_text(raw_shape):
    """
    Cleans the raw ShEx shape by preserving full information while removing unnecessary characters.
    Handles cases where properties have cardinality constraints (e.g., {2}, {6}).
    """
    cleaned_lines = []
    
    for line in raw_shape.split("\n"):
        # Match lines with property declarations and comments, including optional cardinality constraints {n}
        match = re.match(r"^\s*(wdt:P\d+)\s+([\w:]+)\s*(\{\d+\})?\s*;\s*//\s*rdfs:comment\s*\"P\d+\s*-->\s*(.*?)\"\s*", line)
        
        if match:
            property_id, value_type, cardinality, description = match.groups()
            cardinality_str = f" {cardinality}" if cardinality else ""  # Keep cardinality if present
            cleaned_line = f"   {property_id} {value_type}{cardinality_str}  -->  {description}"
            cleaned_lines.append(cleaned_line)
        else:
            cleaned_lines.append(line)  # Preserve unchanged lines

    return "\n".join(cleaned_lines)

def extract_shape(entity_id, named_entity):
    """
    Extracts the ShEx shape for a given entity from Wikidata.
    """
    try:
        # Format named entity: replace spaces with underscores for consistency
        named_entity_formatted = named_entity.replace(" ", "_")  

        # Define shape map including named entity
        shape_map_raw = f"<http://www.wikidata.org/entity/{entity_id}>@<Shape entry point: http://www.wikidata.org/entity/{entity_id} = {named_entity_formatted}>"

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
        print(f"❌ Error extracting shape for {entity_id}: {e}")
        return ""

def process_json(json_file, shape_output_path):
    """
    Processes the JSON file and generates ShEx files for each entity in each question-answer pair.
    Uses the original dataset IDs for naming the output files.
    """
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    for entry in data:
        # Use the original dataset's question ID
        original_id = entry.get("id")

        # Extract named entities from LLM (list of names)
        named_entities = entry.get("llm_extracted_entity_names", [])

        # Extract entity mappings from Wikidata resolution (dictionary)
        entity_dict = entry.get("wikidata_entities_resolved", {})

        if not named_entities or not entity_dict:
            print(f"⚠️ Warning: Skipping question ID {original_id} due to missing entity data.")
            continue  # Skip if data is incomplete

        combined_shex = ""  # Store all shapes for the question
        prefix_block = None  # Stores the prefixes once

        # Iterate over named entities and retrieve their corresponding Q-IDs
        for named_entity in named_entities:
            entity_id = entity_dict.get(named_entity, None)  # Get Q-ID for entity name

            if entity_id:
                shape = extract_shape(entity_id, named_entity)
                if shape:
                    # Extract the prefix block (assumed at the start of the ShEx)
                    if prefix_block is None:
                        prefix_block_match = re.search(r"^(PREFIX .*\n)+", shape)
                        if prefix_block_match:
                            prefix_block = prefix_block_match.group(0)
                    
                    # Remove any duplicate prefix block from the entity shape
                    shape = re.sub(r"^(PREFIX .*\n)+", "", shape)
                    
                    # Append the cleaned entity shape
                    combined_shex += shape + "\n\n"

        # Save combined shape to file
        if combined_shex:
            os.makedirs(shape_output_path, exist_ok=True)
            filename = f"question_{original_id}_shape.shex"  # Use original dataset ID
            output_filepath = os.path.join(shape_output_path, filename)

            # Prepend the prefix block (only once)
            final_shape = clean_shape_text((prefix_block or "") + "\n" + combined_shex)

            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(final_shape.strip())

            print(f"✅ Saved combined ShEx shape for question {original_id} to {output_filepath}")

def main():
    parser = argparse.ArgumentParser(description="Extract ShEx schemas from Wikidata entities found in a JSON dataset.")
    parser.add_argument("--target_json_file", type=str, required=True, help="Path to the JSON file containing extracted entities.")
    parser.add_argument("--shape_output_path", type=str, required=True, help="Path to save the extracted shapes.")

    args = parser.parse_args()
    
    process_json(args.target_json_file, args.shape_output_path)

if __name__ == "__main__":
    main()
