import json
import argparse
import requests
import time

def query_sparql_endpoint(sparql_query, endpoint_url):
    """Executes a SPARQL query against the given endpoint and returns the response."""
    headers = {
        "User-Agent": "SPARQLQueryBot/1.0 (contact: example@example.com)"
    }
    data = {
        "query": sparql_query,
        "format": "json"
    }

    try:
        response = requests.get(endpoint_url, headers=headers, params=data)
        response.raise_for_status()  # Raise error for bad responses (4xx, 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def process_json(json_path, sparql_endpoint_url):
    """Processes the JSON file, executes both SPARQL queries, and appends the results."""
    
    # Load JSON data
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Iterate over entries and execute both SPARQL queries
    for entry in data:
        question_id = entry.get("id", "unknown")

        # Execute and store baseline SPARQL query response
        baseline_sparql_query = entry.get("sparql_query")
        if baseline_sparql_query:
            print(f"🔍 Executing baseline SPARQL query for question ID {question_id}...")
            entry["baseline_sparql_query_response"] = query_sparql_endpoint(baseline_sparql_query, sparql_endpoint_url)
        else:
            print(f"⚠️ Warning: No baseline SPARQL query found for question ID {question_id}")

        # Execute and store LLM-generated SPARQL query response
        llm_generated_sparql = entry.get("llm_generated_sparql")
        if llm_generated_sparql:
            print(f"🔍 Executing LLM-generated SPARQL query for question ID {question_id}...")
            entry["sparql_endpoint_response"] = query_sparql_endpoint(llm_generated_sparql, sparql_endpoint_url)
        else:
            print(f"⚠️ Warning: No LLM-generated SPARQL query found for question ID {question_id}")

        # Avoid hitting the rate limit, add a short delay
        time.sleep(1)

    # Save updated JSON
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"✅ All queries executed. Updated JSON saved to {json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute SPARQL queries from a JSON file and save responses.")
    parser.add_argument("--json_path", type=str, required=True, help="Path to the JSON file with SPARQL queries.")
    parser.add_argument("--sparql_endpoint_url", type=str, required=True, help="SPARQL endpoint URL.")

    args = parser.parse_args()
    
    process_json(args.json_path, args.sparql_endpoint_url)
