import json
import argparse
import requests
import time
from rdflib import Graph

def query_sparql_endpoint(sparql_query, endpoint_url):
    """Executes a SPARQL query against a remote endpoint and returns result values."""
    headers = {
        "User-Agent": "SPARQLQueryBot/1.0 (contact: example@example.com)"
    }
    data = {
        "query": sparql_query,
        "format": "json"
    }

    try:
        response = requests.get(endpoint_url, headers=headers, params=data)
        response.raise_for_status()
        json_response = response.json()

        values = [
            binding[var]["value"]
            for var in json_response.get("head", {}).get("vars", [])
            for binding in json_response.get("results", {}).get("bindings", [])
            if var in binding and "value" in binding[var]
        ]
        return values
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def query_local_graph(sparql_query, graph_path):
    """Executes a SPARQL query against a local RDF graph and returns result values."""
    try:
        g = Graph()
        g.parse(graph_path, format=guess_format(graph_path))

        qres = g.query(sparql_query)
        values = []

        for row in qres:
            for val in row:
                values.append(str(val))

        return values
    except Exception as e:
        return {"error": str(e)}

def guess_format(path):
    """Heuristic to guess RDF serialization based on file extension."""
    if path.endswith(".ttl"):
        return "turtle"
    elif path.endswith(".rdf") or path.endswith(".xml"):
        return "xml"
    elif path.endswith(".nt"):
        return "nt"
    elif path.endswith(".jsonld"):
        return "json-ld"
    else:
        return "turtle"  # default

def process_json(json_path, sparql_endpoint_url, is_local_graph=False, local_graph_location=None):
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    for entry in data:
        question_id = entry.get("id", "unknown")

        baseline_query = entry.get("sparql_query")
        llm_query = entry.get("llm_generated_sparql")

        if baseline_query:
            print(f"🔍 Executing baseline SPARQL query for question ID {question_id}...")
            if is_local_graph:
                entry["baseline_sparql_query_response"] = query_local_graph(baseline_query, local_graph_location)
            else:
                entry["baseline_sparql_query_response"] = query_sparql_endpoint(baseline_query, sparql_endpoint_url)
        else:
            print(f"⚠️ No baseline SPARQL query for question ID {question_id}")

        if llm_query:
            print(f"🔍 Executing LLM-generated SPARQL query for question ID {question_id}...")
            if is_local_graph:
                entry["sparql_endpoint_response"] = query_local_graph(llm_query, local_graph_location)
            else:
                entry["sparql_endpoint_response"] = query_sparql_endpoint(llm_query, sparql_endpoint_url)
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
    parser.add_argument("--is_local_graph", type=bool, required=True, help="Set True or False.")
    parser.add_argument("--local_graph_location", type=str, help="Path to the local RDF graph file (e.g., .ttl, .rdf).")

    args = parser.parse_args()

    if args.is_local_graph and not args.local_graph_location:
        parser.error("--local_graph_location is required when --is_local_graph is set.")

    process_json(
        args.json_path,
        args.sparql_endpoint_url,
        is_local_graph=args.is_local_graph,
        local_graph_location=args.local_graph_location
    )
