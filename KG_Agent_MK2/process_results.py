import json
import argparse
import os

def process_results(json_path, output_file):
    """Processes SPARQL comparison results and generates an overview of the evaluation."""

    # Load JSON data
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Initialize counters and aggregators
    total_entries = len(data)
    valid_entries = 0
    invalid_baseline_count = 0
    invalid_sparql_response_count = 0
    correct_predictions = 0

    total_precision = 0
    total_recall = 0
    total_f1_score = 0

    for entry in data:
        comparison_result = entry.get("sparql_comparison_result", {})
        
        if not comparison_result:
            continue  # Skip if no comparison data available
        
        valid_entries += 1

        # Extract relevant fields
        baseline_entities = comparison_result.get("baseline_entities", [])
        llm_entities = comparison_result.get("llm_entities", [])
        is_correct = comparison_result.get("is_correct", False)
        precision = comparison_result.get("precision", 0)
        recall = comparison_result.get("recall", 0)
        f1_score = comparison_result.get("f1_score", 0)

        # Count valid and invalid queries
        if not baseline_entities:
            invalid_baseline_count += 1  # Faulty original dataset SPARQL query
        if not llm_entities:
            invalid_sparql_response_count += 1  # No results from generated SPARQL query

        if is_correct:
            correct_predictions += 1

        # Aggregate precision, recall, and F1-score
        total_precision += precision
        total_recall += recall
        total_f1_score += f1_score

    # Compute averages
    avg_precision = total_precision / valid_entries if valid_entries else 0
    avg_recall = total_recall / valid_entries if valid_entries else 0
    avg_f1_score = total_f1_score / valid_entries if valid_entries else 0
    accuracy = correct_predictions / valid_entries if valid_entries else 0

    # Generate summary report
    report = f"""
SPARQL Comparison Results Overview
----------------------------------
Total Queries Processed: {total_entries}
Valid Comparisons: {valid_entries}

✅ Correct Predictions: {correct_predictions} ({accuracy:.2%})
❌ Invalid Baseline Queries: {invalid_baseline_count}
❌ Invalid LLM SPARQL Responses: {invalid_sparql_response_count}

📊 Average Precision: {avg_precision:.4f}
📊 Average Recall: {avg_recall:.4f}
📊 Average F1-Score: {avg_f1_score:.4f}
"""

    # Write to output file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ Processed results saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate SPARQL comparison results and generate an overview.")
    parser.add_argument("--json_path", type=str, required=True, help="Path to the JSON file with comparison results.")
    parser.add_argument("--output_dir", type=str, required=True, help="Output file to save processed results.")

    args = parser.parse_args()

    process_results(args.json_path, args.output_dir)
