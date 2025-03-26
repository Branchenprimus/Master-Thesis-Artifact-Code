import json
import argparse

def compare_sparql_results(entry):
    """Compares baseline and LLM-generated SPARQL query responses based on entity overlap."""
    question_id = entry.get("id", "unknown")

    baseline_entities = set(entry.get("baseline_sparql_query_response", []))
    llm_entities = set(entry.get("sparql_endpoint_response", []))

    if not baseline_entities:
        is_correct = "Invalid"
        intersection = set()
    else:
        intersection = baseline_entities & llm_entities
        is_correct = "True" if baseline_entities == llm_entities else "False"

    print(f"Question ID: {question_id}")
    print(f"Baseline Entities: {baseline_entities}")
    print(f"LLM Entities: {llm_entities}")
    print(f"Is Correct: {is_correct}")

    return {
        "baseline_entities": list(baseline_entities),
        "llm_entities": list(llm_entities),
        "is_correct": is_correct
    }

def process_json(json_path):
    """Processes the JSON file, compares SPARQL query results, and appends the comparison results to the JSON file."""

    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    total = 0
    correct = 0

    for entry in data:
        comparison_result = compare_sparql_results(entry)
        if comparison_result:
            entry["sparql_comparison_result"] = comparison_result

            # Only consider valid entries for accuracy
            if comparison_result["is_correct"] != "Invalid":
                total += 1
                if comparison_result["is_correct"] == "True":
                    correct += 1

    execution_accuracy = (correct / total * 100) if total > 0 else 0.0

    print(f"\n📊 Execution Accuracy: {execution_accuracy:.2f}% ({correct}/{total} correct)")

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"✅ Comparison results and accuracy appended to {json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare SPARQL query results using entity overlap.")
    parser.add_argument("--json_path", type=str, required=True, help="Path to the JSON file with SPARQL query responses.")

    args = parser.parse_args()
    
    process_json(args.json_path)
