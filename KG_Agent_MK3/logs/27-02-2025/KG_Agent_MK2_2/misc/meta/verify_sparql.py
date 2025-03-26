import json
import argparse

def extract_values(response):
    """Extracts only 'value' fields from a SPARQL response."""
    if not response or "results" not in response or "bindings" not in response["results"]:
        return set()  # Return empty set if response is invalid

    return {
        binding[var]["value"]
        for var in response.get("head", {}).get("vars", [])
        for binding in response["results"]["bindings"]
        if var in binding and "value" in binding[var]
    }

def compare_sparql_results(entry):
    """Compares baseline and LLM-generated SPARQL query responses based on entity overlap."""
    question_id = entry.get("id", "unknown")

    baseline_response = entry.get("baseline_sparql_query_response", {})
    llm_response = entry.get("sparql_endpoint_response", {})

    # Extract only "value" fields for comparison
    baseline_entities = extract_values(baseline_response)
    llm_entities = extract_values(llm_response)

    # Compute similarity metrics
    intersection = baseline_entities & llm_entities  # Common entities
    precision = len(intersection) / len(llm_entities) if llm_entities else 0
    recall = len(intersection) / len(baseline_entities) if baseline_entities else 0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Determine correctness (Entities match regardless of order)
    is_correct = baseline_entities == llm_entities  # True if sets are identical

    return {
        "baseline_entities": list(baseline_entities),
        "llm_entities": list(llm_entities),
        "common_entities": list(intersection),
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "is_correct": is_correct  # Mark as true if sets match
    }


def process_json(json_path):
    """Processes the JSON file, compares SPARQL query results, and appends the comparison results to the JSON file."""
    
    # Load JSON data
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Iterate over entries and compare responses
    for entry in data:
        comparison_result = compare_sparql_results(entry)
        if comparison_result:
            entry["sparql_comparison_result"] = comparison_result

    # Save updated JSON (overwrite with appended comparison results)
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"✅ Comparison results appended to {json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare SPARQL query results using entity overlap.")
    parser.add_argument("--json_path", type=str, required=True, help="Path to the JSON file with SPARQL query responses.")

    args = parser.parse_args()
    
    process_json(args.json_path)
