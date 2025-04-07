import json
import argparse

def compare_sparql_results(entry):
    """Compares baseline and LLM-generated SPARQL query responses for a single question."""
    baseline = set(entry.get("baseline_sparql_query_response", []))
    llm = set(entry.get("sparql_endpoint_response", []))
    
    comparison = {
        "baseline_entities": list(baseline),
        "llm_entities": list(llm),
        "is_correct": "Invalid" if not baseline else "True" if baseline == llm else "False"
    }
    
    entry["sparql_comparison_result"] = comparison
    return comparison

def process_single_question(json_path, question_index):
    """Processes and updates a single question in the JSON file."""
    try:
        with open(json_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            
            if question_index < 0 or question_index >= len(data):
                raise ValueError(f"Invalid question index {question_index}")
            
            entry = data[question_index]
            result = compare_sparql_results(entry)
            
            # Update file
            f.seek(0)
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.truncate()
            
            print(f"Question ID: {entry.get('id', 'unknown')}")
            print(f"Match: {result['is_correct']}")
            print(f"Baseline: {len(result['baseline_entities'])} results")
            print(f"LLM: {len(result['llm_entities'])} results")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify SPARQL results for a single question")
    parser.add_argument("--json_path", required=True, help="Path to JSON file")
    parser.add_argument("--question_index", type=int, required=True, help="Question index to verify")
    
    args = parser.parse_args()
    process_single_question(args.json_path, args.question_index)