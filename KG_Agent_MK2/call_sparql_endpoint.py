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
        print(f"baseline_sparql_query: {baseline_query}")
        llm_queries = entry.get("LLM_generated_sparql_query", [])
        llm_query = llm_queries[-1]["query"] if llm_queries else None
        print(f"llm_generated_sparql: {llm_query}")


        if baseline_query:
            print(f"\n🔍 Executing baseline SPARQL query for question ID {question_id}...")
            if is_local_graph:
                entry["baseline_sparql_query_response"] = Utils.query_local_graph(baseline_query, local_graph_location)
            else:
                response = Utils.query_sparql_endpoint(baseline_query, sparql_endpoint_url)
                print(f"baseline_sparql_query_response: {response}")
                print(f"baseline_query: {baseline_query}")
                print(f"sparql_endpoint_url: {sparql_endpoint_url}")
                entry["baseline_sparql_query_response"] = response
        else:
            print(f"⚠️ No baseline SPARQL query for question ID {question_id}")

        if llm_query:
            print(f"🔍 Executing LLM-generated SPARQL query for question ID {question_id}...")
            if is_local_graph:
                entry["llm_generated_sparql_query_response"] = Utils.query_local_graph(llm_query, local_graph_location)
            else:
                response = Utils.query_sparql_endpoint(llm_query, sparql_endpoint_url)
                print(f"llm_generated_sparql_query_response: {baseline_query}")
                print(f"baseline_query: {baseline_query}")
                print(f"sparql_endpoint_url: {sparql_endpoint_url}")
                entry["llm_generated_sparql_query_response"] = response
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
        args.is_local_graph,
        args.local_graph_location
    )
