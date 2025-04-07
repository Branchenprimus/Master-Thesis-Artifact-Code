import argparse
import json
import os
import re
from shexer.shaper import Shaper

def clean_shape_text(raw_shape):
    """
    Cleans the raw ShEx shape while preserving essential information.
    """
    cleaned_lines = []
    for line in raw_shape.split("\n"):
        match = re.match(r"^\s*(wdt:P\d+)\s+([\w:]+)\s*(\{\d+\})?\s*;?\s*//\s*rdfs:comment\s*\"P\d+\s*-->\s*(.*?)\"\s*", line)
        if match:
            property_id, value_type, cardinality, description = match.groups()
            cardinality_str = f" {cardinality}" if cardinality else ""
            cleaned_line = f"   {property_id} {value_type}{cardinality_str}  -->  {description}"
            cleaned_lines.append(cleaned_line)
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def extract_shape(entity_id, named_entity):
    """
    Extracts ShEx shape for a single entity from Wikidata.
    """
    try:
        named_entity_formatted = named_entity.replace(" ", "_")  
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

def process_single_question(json_file, shape_output_path, question_index):
    """
    Processes one question specified by index from the input JSON.
    """
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Input JSON should be a list of questions")

    if question_index < 0 or question_index >= len(data):
        raise ValueError(f"Question index {question_index} out of range (0-{len(data)-1})")

    entry = data[question_index]
    original_id = entry.get("id")
    named_entities = entry.get("llm_extracted_entity_names", [])
    entity_dict = entry.get("wikidata_entities_resolved", {})

    if not named_entities or not entity_dict:
        print(f"⚠️ Skipping question {original_id}: missing entity data")
        return

    combined_shex = ""
    prefix_block = None

    for named_entity in named_entities:
        entity_id = entity_dict.get(named_entity)
        if entity_id:
            shape = extract_shape(entity_id, named_entity)
            if shape:
                if prefix_block is None:
                    prefix_block_match = re.search(r"^(PREFIX .*\n)+", shape)
                    prefix_block = prefix_block_match.group(0) if prefix_block_match else ""
                shape = re.sub(r"^(PREFIX .*\n)+", "", shape)
                combined_shex += shape + "\n\n"

    if combined_shex:
        os.makedirs(shape_output_path, exist_ok=True)
        filename = f"question_{original_id}_shape.shex"
        output_path = os.path.join(shape_output_path, filename)
        
        final_shape = clean_shape_text(f"{prefix_block}\n{combined_shex}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_shape.strip())
        print(f"✅ Saved shape for question {original_id} to {output_path}")

def generate_local_shape(local_graph_path, shape_output_path):
    """
    Generates global shape for local graph (non-question-specific).
    """
    try:
        shaper = Shaper(
            graph_file_input=local_graph_location,
            input_format="xml",  # Assuming the format of the local graph file is RDF/XML
            disable_comments=True,
            all_classes_mode=True
        )
        shape = shaper.shex_graph(string_output=True)
        
        os.makedirs(shape_output_path, exist_ok=True)
        output_path = os.path.join(shape_output_path, "local_graph_shape.shex")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(shape.strip())
        print(f"✅ Global local graph shape saved to {output_path}")
    except Exception as e:
        print(f"❌ Local graph error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate ShEx shapes per question")
    parser.add_argument("--target_json_file", type=str, required=True)
    parser.add_argument("--shape_output_path", type=str, required=True)
    parser.add_argument("--is_local_graph", type=bool, required=True)
    parser.add_argument("--local_graph_location", type=str)
    parser.add_argument("--question_index", type=int, default=0)

    args = parser.parse_args()

    if args.is_local_graph:
        if not args.local_graph_location:
            print("❌ Missing local graph path")
            return
        generate_local_shape(args.local_graph_location, args.shape_output_path)
    else:
        process_single_question(
            args.target_json_file,
            args.shape_output_path,
            args.question_index
        )

if __name__ == "__main__":
    main()