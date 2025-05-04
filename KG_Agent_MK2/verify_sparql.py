import json
import argparse
import time
from utility import Utils

def compare_sparql_results(entry):
    """Compares baseline and LLM-generated SPARQL query responses based on entity overlap."""
    question_id = entry.get("baseline_id", "unknown")

    baseline_entities = set(entry.get("baseline_sparql_query_response", []))
    
    llm_queries = entry.get("LLM_generated_sparql_query", [])
    llm_entities = set(llm_queries[-1]["result"]) if llm_queries else None
    
    print(f"First 5 baseline_entities: {list(baseline_entities)[:5] if baseline_entities else 'None'}")
    print(f"First 5 llm_entities: {list(llm_entities)[:5] if llm_entities else 'None'}")
    

    if not baseline_entities:
        is_correct = "Invalid"
    else:
        is_correct = "True" if baseline_entities == llm_entities else "False"

    print(f"Question ID: {question_id}")
    print(f"Is Correct: {is_correct}")

    return is_correct

def process_json(json_path, sparql_endpoint_url, is_local_graph, local_graph_location):
    """Processes the JSON file, compares SPARQL query results, and appends the comparison results to the JSON file."""

    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    correct = 0
    total = 0

    for entry in data:
        question_id = entry.get("baseline_id", "unknown")

        # Baseline SPARQL query
        baseline_query = entry.get("baseline_sparql_query")
        print(f"\nbaseline_sparql_query: {baseline_query}")

        # LLM-generated SPARQL query
        llm_queries = entry.get("LLM_generated_sparql_query", [])
        llm_query = llm_queries[-1]["query"] if llm_queries else None
        print(f"llm_generated_sparql_query: {llm_query}")

        # Execute baseline query
        if baseline_query:
            print(f"🔍 Executing baseline SPARQL query for question ID {question_id}...")
            if is_local_graph:
                response = Utils.query_local_graph(baseline_query, local_graph_location)
                entry["baseline_sparql_query_response"] = response

            else:
                response = Utils.query_sparql_endpoint(baseline_query, sparql_endpoint_url)
                entry["baseline_sparql_query_response"] = response
                
        else:
            print(f"⚠️ No baseline SPARQL query for question ID {question_id}")

        # Result comparison and accuracy calculation
        comparison_result = compare_sparql_results(entry)
        if comparison_result:
            entry["sparql_comparison_result"]["is_correct"] = comparison_result

            if comparison_result != "Invalid":
                total += 1
                if comparison_result == "True":
                    correct += 1

        # Optional sleep to avoid overloading endpoint
        time.sleep(1)

    # Final accuracy and output
    execution_accuracy = (correct / total * 100) if total > 0 else 0.0
    print(f"\n📊 Execution Accuracy: {execution_accuracy:.2f}% ({correct}/{total} correct)")

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"✅ All queries executed and results saved to {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare SPARQL query results using entity overlap.")
    parser.add_argument("--json_path", type=str, required=True, help="Path to the JSON file with SPARQL query responses.")
    parser.add_argument("--sparql_endpoint_url", type=str, help="SPARQL endpoint URL (ignored if --is_local_graph is used).")
    parser.add_argument("--is_local_graph", type=Utils.str_to_bool, required=True, help="Set True or False.")
    parser.add_argument("--local_graph_location", type=str, help="Path to the local RDF graph file (e.g., .ttl, .rdf).")

    args = parser.parse_args()
    
    process_json(args.json_path, args.sparql_endpoint_url, args.is_local_graph, args.local_graph_location)
