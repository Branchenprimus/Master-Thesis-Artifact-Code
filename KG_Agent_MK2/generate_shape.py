import argparse
import json
import os
import re   
from rdflib import Graph, Namespace, URIRef, RDFS
from shexer.shaper import Shaper
from utility import Utils

from shexer.shaper import Shaper
from rdflib import Graph
import os

def generate_shape_from_local_graph(local_graph_location, shape_output_path, annotation):
    """
    Loads all RDF files from a folder, generates ShEx shapes using Shexer,
    and annotates shape lines with labels using rdflib.
    """
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

        # Annotate shape using labels from graph
        if annotation:
            print("📜 Annotating shape with labels...")
            annotate_local_shape_file(output_filepath, rdf_graph=g)

    except Exception as e:
        print(f"❌ Error generating shape from local graph: {e}")


def annotate_local_shape_file(shape_file_path, rdf_file_path):
    """
    Rewrites SHEx shape lines by appending --> label using rdflib from a local RDF file.
    """
    property_pattern = re.compile(r"^\s*(wdt:P\d+)\s+([\w:]+)\s*(\{\d+\})?\s*;?\s*$")
    
    with open(shape_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    used_properties = set()
    for line in lines:
        match = property_pattern.match(line)
        if match:
            used_properties.add(match.group(1))

    # Load RDF graph
    g = Graph()
    g.parse(rdf_file_path)

    WDT = Namespace("http://www.wikidata.org/prop/direct/")
    label_map = {}

    for prop in used_properties:
        prop_id = prop.split(":")[-1]
        prop_uri = WDT[prop_id]
        label = g.label(prop_uri)
        if label:
            label_map[prop] = str(label)

    # Rewrite lines with annotations
    rewritten_lines = []
    for line in lines:
        match = property_pattern.match(line)
        if match:
            prop, datatype, cardinality = match.groups()
            label = label_map.get(prop)
            cardinality_str = f" {cardinality}" if cardinality else ""
            if label:
                rewritten_line = f"   {prop} {datatype}{cardinality_str}  -->  {label}"
                rewritten_lines.append(rewritten_line)
            else:
                rewritten_lines.append(line.rstrip())
        else:
            rewritten_lines.append(line.rstrip())

    output_path = shape_file_path.replace(".shex", ".annotated.shex")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rewritten_lines))

    print(f"✅ Annotated local shape saved to {output_path}")


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

def generate_combined_shape_from_wikidata(entity_label_pairs, annotation):
    shape_map_lines = [
        f"<http://www.wikidata.org/entity/{entity_id}>@<Shape entry point: http://www.wikidata.org/entity/{entity_id} = {label.replace(' ', '_')}>"
        for label, entity_id in entity_label_pairs
    ]
    shape_map_raw = "\n".join(shape_map_lines)

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
        wikidata_annotation=annotation,
    )

    return shaper.shex_graph(string_output=True)


def process_json(json_file, shape_output_path, annotation):
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    for entry in data:
        original_id = entry.get("baseline_id")
        named_entities = entry.get("llm_extracted_entity_names", [])
        entity_dict = entry.get("wikidata_entities_resolved", {})

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

        # Generate one combined shape for all entities in this question
        shape = generate_combined_shape_from_wikidata(entity_label_pairs, annotation)
        if shape:
            prefix_block_match = re.search(r"^(PREFIX .*\n)+", shape)
            prefix_block = prefix_block_match.group(0) if prefix_block_match else ""
            shape = re.sub(r"^(PREFIX .*\n)+", "", shape)

            final_shape = clean_shape_text(prefix_block + "\n" + shape)

            os.makedirs(shape_output_path, exist_ok=True)
            output_filepath = os.path.join(shape_output_path, f"question_{original_id}_shape.shex")
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(final_shape.strip())

            print(f"✅ Saved combined ShEx shape for question {original_id} to {output_filepath}")


def main():
    parser = argparse.ArgumentParser(description="Extract ShEx schemas from Wikidata entities found in a JSON dataset.")
    parser.add_argument("--target_json_file", type=str, required=True, help="Path to the JSON file containing extracted entities.")
    parser.add_argument("--shape_output_path", type=str, required=True, help="Path to save the extracted shapes.")
    parser.add_argument("--is_local_graph", type=Utils.str_to_bool, required=True, help="Set True or False.")
    parser.add_argument("--local_graph_location", type=str, required=False, help="Path to the local graph file.")
    parser.add_argument("--annotation", type=Utils.str_to_bool, required=True, help="Path to the local graph file.")

    args = parser.parse_args()
    is_local_graph = args.is_local_graph
    
    print(f"✅ is_local_graph: {is_local_graph}")
    
    if is_local_graph:
        if not args.local_graph_location:
            print("❌ Error: --local_graph_location is required when --is_local_graph is True.")
            return
        print(f"✅ Generating shape from local graph at {args.local_graph_location}")
        generate_shape_from_local_graph(args.local_graph_location, args.shape_output_path, args.annotation)
    else:
        print(f"✅ Generating shape using sparql endpoint {args.target_json_file} and generated shapes.")
        process_json(args.target_json_file, args.shape_output_path, args.annotation)

if __name__ == "__main__":
    main()
