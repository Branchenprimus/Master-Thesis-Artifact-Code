import json
import argparse
import requests
import time
from rdflib import Graph
from utility import Utils

def process_json(json_path, sparql_endpoint_url, is_local_graph=False, local_graph_location=None):
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    for entry in data:
        question_id = entry.get("baseline_id", "unknown")

        baseline_query = entry.get("baseline_sparql_query")
        llm_query = entry.get("llm_generated_sparql")

        if baseline_query:
            print(f"🔍 Executing baseline SPARQL query for question ID {question_id}...")
            if is_local_graph:
                entry["baseline_sparql_query_response"] = Utils.query_local_graph(baseline_query, local_graph_location)
            else:
                entry["baseline_sparql_query_response"] = Utils.query_sparql_endpoint(baseline_query, sparql_endpoint_url)
        else:
            print(f"⚠️ No baseline SPARQL query for question ID {question_id}")

        if llm_query:
            print(f"🔍 Executing LLM-generated SPARQL query for question ID {question_id}...")
            if is_local_graph:
                entry["sparql_endpoint_response"] = Utils.query_local_graph(llm_query, local_graph_location)
            else:
                entry["sparql_endpoint_response"] = Utils.query_sparql_endpoint(llm_query, sparql_endpoint_url)
        else:
            print(f"⚠️ No LLM-generated SPARQL query for question ID {question_id}")

        time.sleep(1)

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"✅ All queries executed. Updated JSON saved to {json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute SPARQL queries from a JSON file and save responses.")
    parser.add_argument("--json_path", type=str, required=True, help="Path to the JSON file with SPARQL queries.")
    parser.add_argument("--sparql_endpoint_url", type=str, help="SPARQL endpoint URL (ignored if --is_local_graph is used).")
    parser.add_argument("--is_local_graph", type=Utils.str_to_bool, required=True, help="Set True or False.")
    parser.add_argument("--local_graph_location", type=str, help="Path to the local RDF graph file (e.g., .ttl, .rdf).")

    args = parser.parse_args()
    is_local_graph = args.is_local_graph

    if is_local_graph and not args.local_graph_location:
        parser.error("--local_graph_location is required when --is_local_graph is set.")

    process_json(
        args.json_path,
        args.sparql_endpoint_url,
        is_local_graph=is_local_graph,
        local_graph_location=args.local_graph_location
    )
