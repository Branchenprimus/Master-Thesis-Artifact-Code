import json
import argparse
import requests
import time
from rdflib import Graph

def query_sparql_endpoint(sparql_query, endpoint_url):
    """Executes a SPARQL query against a remote endpoint."""
    headers = {"User-Agent": "SPARQLQueryBot/1.0"}
    params = {"query": sparql_query, "format": "json"}
    
    try:
        response = requests.get(endpoint_url, headers=headers, params=params)
        response.raise_for_status()
        return [result["value"] for result in response.json().get("results", {}).get("bindings", [])]
    except Exception as e:
        return {"error": str(e)}

def query_local_graph(sparql_query, graph_path):
    """Executes a SPARQL query against a local RDF graph."""
    try:
        g = Graph()
        g.parse(graph_path, format=guess_format(graph_path))
        return [str(val) for row in g.query(sparql_query) for val in row]
    except Exception as e:
        return {"error": str(e)}

def guess_format(path):
    """Guesses RDF format from file extension."""
    ext = path.split(".")[-1].lower()
    return {
        "ttl": "turtle",
        "rdf": "xml",
        "xml": "xml",
        "nt": "nt",
        "jsonld": "json-ld"
    }.get(ext, "turtle")

def process_single_question(args):
    """Processes one question specified by index."""
    try:
        with open(args.json_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            
            # Validate index
            if args.question_index < 0 or args.question_index >= len(data):
                raise ValueError(f"Invalid question index {args.question_index}")
            
            entry = data[args.question_index]
            question_id = entry.get("id", str(args.question_index))
            
            # Process baseline query
            if "sparql_query" in entry:
                if args.is_local_graph:
                    entry["baseline_response"] = query_local_graph(
                        entry["sparql_query"], 
                        args.local_graph_location
                    )
                else:
                    entry["baseline_response"] = query_sparql_endpoint(
                        entry["sparql_query"], 
                        args.sparql_endpoint_url
                    )
            
            # Process LLM-generated query
            if "llm_generated_sparql" in entry:
                if args.is_local_graph:
                    entry["llm_response"] = query_local_graph(
                        entry["llm_generated_sparql"], 
                        args.local_graph_location
                    )
                else:
                    entry["llm_response"] = query_sparql_endpoint(
                        entry["llm_generated_sparql"], 
                        args.sparql_endpoint_url
                    )
            
            # Save updated data
            f.seek(0)
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.truncate()
            
            print(f"✅ Processed question {question_id} (index {args.question_index})")
            time.sleep(1)  # Rate limiting
            
    except Exception as e:
        print(f"❌ Error processing question: {e}")
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute SPARQL queries for a single question")
    parser.add_argument("--json_path", required=True, help="Path to JSON file")
    parser.add_argument("--sparql_endpoint_url", help="SPARQL endpoint URL")
    parser.add_argument("--is_local_graph", type=bool, required=True, help="Use local graph")
    parser.add_argument("--local_graph_location", help="Path to local RDF file")
    parser.add_argument("--question_index", type=int, required=True, help="Question index to process")
    
    args = parser.parse_args()
    
    # Validation
    if args.is_local_graph and not args.local_graph_location:
        parser.error("Local graph requires --local_graph_location")
    
    if not args.is_local_graph and not args.sparql_endpoint_url:
        parser.error("Remote SPARQL endpoint requires --sparql_endpoint_url")
    
    process_single_question(args)