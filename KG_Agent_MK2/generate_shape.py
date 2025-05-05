import argparse
import json
import os
import re   
import traceback
import sys
from rdflib import Graph
from shexer.consts import SHACL_TURTLE
from shexer.shaper import Shaper
from utility import Utils
import time

def generate_shape_from_local_graph(local_graph_location, shape_output_path, shape_type, existing_shape_path):
    """
    Loads all RDF files from a folder, generates ShEx shapes using Shexer,
    and annotates shape lines with labels using rdflib.
    """
    if shape_type == "shex":
        try:
            g = Graph()

            for fname in os.listdir(local_graph_location):
                if fname.endswith((".ttl", ".rdf", ".nt")):
                    fpath = os.path.join(local_graph_location, fname)
                    fmt = (
                        "ttl" if fname.endswith(".ttl")
                        else "nt" if fname.endswith(".nt")
                        else "xml"
                    )
                    print(f"📥 Loading {fname} as {fmt}")
                    g.parse(fpath, format=fmt)

            if len(g) == 0:
                print(f"⚠️ No RDF triples loaded from {local_graph_location}")
                return

            # Generate shapes from combined graph
            shaper = Shaper(
                rdflib_graph=g,
                all_classes_mode=True,
                disable_comments=True
            )

            shape = shaper.shex_graph(string_output=True)
            os.makedirs(shape_output_path, exist_ok=True)
            output_filepath = os.path.join(shape_output_path, "local_graph_shape.shex")

            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(shape.strip())

            print(f"✅ Saved ShEx shape for local graph to {output_filepath}")

        except Exception as e:
            print(f"❌ Error generating shape from local graph: {e}")
    
    elif shape_type == "shacl":
        if not existing_shape_path or not os.path.isfile(existing_shape_path):
            print(f"❌ Error: Existing shape file not found at {existing_shape_path}")
            return

        os.makedirs(shape_output_path, exist_ok=True)
        output_filepath = os.path.join(shape_output_path, os.path.basename(existing_shape_path))

        try:
            with open(existing_shape_path, "r", encoding="utf-8") as src, open(output_filepath, "w", encoding="utf-8") as dest:
                dest.write(src.read())

            print(f"✅ Copied existing shape file to {output_filepath}")
        except Exception as e:
            print(f"❌ Error copying shape file: {e}")
        


def clean_shape_text(raw_shape):
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

def generate_combined_shape_from_wikidata(entity_label_pairs, shape_type, annotation, sparql_endpoint_url):
    shape_lines = []
    for label, entity_id in entity_label_pairs:
        # Use a unique namespace for the shape label to avoid ambiguity
        shape_label = f"http://shapes.wikidata.org/{label.replace(' ', '_')}:{entity_id}"
        shape_lines.append(f"<http://www.wikidata.org/entity/{entity_id}>@<{shape_label}>")

    shape_map_raw = "\n".join(shape_lines)
    print(f"Generated {shape_type} shape map:\n{shape_map_raw}")

    namespaces_dict = {
        "http://example.org/": "ex",
        "http://www.w3.org/XML/1998/namespace/": "xml",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
        "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
        "http://www.w3.org/2001/XMLSchema#": "xsd",
        "http://xmlns.com/foaf/0.1/": "foaf",
        "http://www.wikidata.org/prop/direct/": "wdt",
        "http://www.wikidata.org/entity/": "wd",
        "http://shapes.wikidata.org/": "shapes"
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
    url_endpoint=sparql_endpoint_url,
    namespaces_dict=namespaces_dict,
    disable_comments=True,
    namespaces_to_ignore=namespaces_to_ignore,
    wikidata_annotation=annotation,
    )
    
    try:

        if shape_type == "shex":
            return shaper.shex_graph(string_output=True)

        elif shape_type == "shacl":
            return shaper.shex_graph(string_output=True, output_format=SHACL_TURTLE)
                
    except Exception as e:
            print("❌ Error generating shape from shape_map:", file=sys.stderr)
            print(f"Entities involved: {entity_label_pairs}", file=sys.stderr)
            print(f"Shape map raw:\n{shape_map_raw}", file=sys.stderr)
            print(f"Exception message: {e}", file=sys.stderr)
            print("Full traceback:", file=sys.stderr)
            traceback.print_exc()  # already goes to stderr

def generate_combined_shape_from_dbpedia(entity_label_pairs, shape_type):
    """
    Generates SHACL shapes from DBpedia entities using a shape map-like structure.
    """
    try:
        shape_lines = []
        for label, entity_id in entity_label_pairs:
            # Use a unique namespace for the shape label to avoid ambiguity
            shape_label = f"http://shapes.dbpedia.org/{label.replace(' ', '_')}:{entity_id}"
            shape_lines.append(f"<{entity_id}>@<{shape_label}>")

        shape_map_raw = "\n".join(shape_lines)
        print(f"Generated shape map:\n{shape_map_raw}")
        namespaces_dict = {
            "http://example.org/": "ex",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
            "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
            "http://www.w3.org/2001/XMLSchema#": "xsd",
            "http://xmlns.com/foaf/0.1/": "foaf",
            "http://dbpedia.org/resource/": "dbr",
            "http://dbpedia.org/ontology/": "dbo",
            "http://dbpedia.org/property/": "dbp",
            "http://dbpedia.org/class/yago/": "yago",
            "http://purl.org/dc/terms/": "dcterms",
            "http://www.w3.org/2002/07/owl#": "owl",
            "http://www.w3.org/2007/05/powder-s#": "powders",
            "http://www.w3.org/ns/prov#": "prov",
            "http://umbel.org/umbel/rc/": "umbel",
            "http://schema.org/": "schema",
            "http://shapes.dbpedia.org/": "shapes"
        }


        shaper = Shaper(
            shape_map_raw=shape_map_raw,
            url_endpoint="https://dbpedia.org/sparql",
            namespaces_dict=namespaces_dict,
            disable_comments=True,
        )

        if shape_type == "shex":
            return shaper.shex_graph(string_output=True)
        elif shape_type == "shacl":
            return shaper.shex_graph(string_output=True, output_format=SHACL_TURTLE)

    except Exception as e:
        print(f"❌ Error generating shape: {e}")
        return None
    
def generate_shape_from_endpoint(json_file, shape_output_path, shape_type, dataset_type, annotation, sparql_endpoint_url):
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    for entry in data:
        original_id = entry.get("baseline_id")
        named_entities = entry.get("llm_extracted_entity_names", [])
        entity_dict = entry.get("endpoint_entities_resolved", {})

        if not named_entities or not entity_dict:
            print(f"⚠️ Warning: Skipping question ID {original_id} due to missing entity data.")
            continue

        # Collect all (label, entity_id) pairs
        entity_label_pairs = []
        for name in named_entities:
            entity_id = entity_dict.get(name.strip())
            if entity_id:
                entity_label_pairs.append((name, entity_id))

        if not entity_label_pairs:
            print(f"⚠️ Warning: No valid entity-label pairs for question ID {original_id}.")
            continue
        
        if dataset_type == "wikidata":
            # Generate ShEx shape for each entity
            shape = generate_combined_shape_from_wikidata(entity_label_pairs, shape_type, annotation, sparql_endpoint_url)
        elif dataset_type == "dbpedia":
            # Generate ShEx shape for each entity
            shape = generate_combined_shape_from_dbpedia(entity_label_pairs, shape_type) 
        
        if shape:
            prefix_block_match = re.search(r"^(PREFIX .*\n)+", shape)
            prefix_block = prefix_block_match.group(0) if prefix_block_match else ""
            shape = re.sub(r"^(PREFIX .*\n)+", "", shape)

            final_shape = clean_shape_text(prefix_block + "\n" + shape)

            os.makedirs(shape_output_path, exist_ok=True)
            output_filepath = os.path.join(shape_output_path, f"question_{original_id}_shape.{shape_type}")
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(final_shape.strip())

            print(f"✅ Saved {shape_type} shape for question {original_id} to {output_filepath}")
            
        time.sleep(1.5)  # adjust if needed


def main():
    parser = argparse.ArgumentParser(description="Extract ShEx schemas from Wikidata entities found in a JSON dataset.")
    parser.add_argument("--target_json_file", type=str, required=True, help="Path to the JSON file containing extracted entities.")
    parser.add_argument("--shape_output_path", type=str, required=True, help="Path to save the extracted shapes.")
    parser.add_argument("--is_local_graph", type=Utils.str_to_bool, required=True, help="Set True or False.")
    parser.add_argument("--local_graph_location", type=str, required=False, help="Path to the local graph file.")
    parser.add_argument("--shape_type", type=str, choices=["shex", "shacl"], required=True, help="Type of shape to generate (shex or shacl).")
    parser.add_argument("--existing_shape_path", type=str, required=False, help="Path to an existing shape file for SHACL generation.")
    parser.add_argument("--dataset_type", type=str, choices=["wikidata", "dbpedia", "corporate_graphs"], required=True, help="Type of dataset (wikidata or dbpedia).")
    parser.add_argument("--annotation", type=Utils.str_to_bool, required=False, help="Annotation for the shape file.")
    parser.add_argument("--sparql_endpoint_url", type=str, required=False, help="SPARQL endpoint URL for DBpedia or Wikidata.")
    parser.add_argument("--baseline_run", type=Utils.str_to_bool, default=False, help="Run baseline SPARQL queries.")
    
    args = parser.parse_args()
    is_local_graph = args.is_local_graph
    
    print(f"✅ is_local_graph: {is_local_graph}")
    if args.baseline_run:
        print("⚠️ Baseline run is enabled. No shape generation will occur.")
        return
    if is_local_graph:
        if not args.local_graph_location:
            print("❌ Error: --local_graph_location is required when --is_local_graph is True.")
            return
        print(f"✅ Generating shape from local graph at {args.local_graph_location}")
        generate_shape_from_local_graph(args.local_graph_location, args.shape_output_path, args.shape_type, args.existing_shape_path)
    else:
        print(f"✅ Generating shape using sparql endpoint {args.target_json_file} and generated shapes.")
        generate_shape_from_endpoint(args.target_json_file, args.shape_output_path, args.shape_type, args.dataset_type, args.annotation, args.sparql_endpoint_url)

if __name__ == "__main__":
    main()
