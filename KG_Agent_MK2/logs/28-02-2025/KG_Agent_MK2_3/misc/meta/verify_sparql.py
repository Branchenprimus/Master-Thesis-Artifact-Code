import json
import argparse

def compare_sparql_results(entry):
    """Compares baseline and LLM-generated SPARQL query responses based on entity overlap."""
    question_id = entry.get("id", "unknown")

    # Extract URIs directly from the new JSON structure
    baseline_entities = set(entry.get("baseline_sparql_query_response", []))
    llm_entities = set(entry.get("sparql_endpoint_response", []))

    # If the baseline_entities set is empty, mark the result as invalid
    if not baseline_entities:
        is_correct = "Invalid"
        precision = 0
        recall = 0
        f1_score = 0
        intersection = set()
    else:
        # Compute similarity metrics
        intersection = baseline_entities & llm_entities  # Common entities
        precision = len(intersection) / len(llm_entities) if llm_entities else 0
        recall = len(intersection) / len(baseline_entities) if baseline_entities else 0
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # Determine correctness (Entities match regardless of order)
        is_correct = "True" if baseline_entities == llm_entities else "False"

    # Log results
    print(f"Question ID: {question_id}")
    print(f"Baseline Entities: {baseline_entities}")
    print(f"LLM Entities: {llm_entities}")
    print(f"Common Entities: {intersection}")
    print(f"Precision: {precision:.2f}")
    print(f"Recall: {recall:.2f}")
    print(f"F1 Score: {f1_score:.2f}")
    print(f"Is Correct: {is_correct}")

    return {
        "baseline_entities": list(baseline_entities),
        "llm_entities": list(llm_entities),
        "common_entities": list(intersection),
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "is_correct": is_correct  # Mark as "Invalid" if baseline_entities is empty
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
