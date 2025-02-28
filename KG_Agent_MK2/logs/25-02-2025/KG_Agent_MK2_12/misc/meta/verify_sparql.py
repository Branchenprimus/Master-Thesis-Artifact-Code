#!/usr/bin/env python3
import json
import argparse
import sys

def extract_values_from_answers(question_entry):
    """Extracts all 'value' URIs from the original dataset's 'answers' field."""
    values = set()
    
    if "answers" in question_entry:
        for answer_set in question_entry["answers"]:
            if "results" in answer_set and "bindings" in answer_set["results"]:
                for binding in answer_set["results"]["bindings"]:
                    for key in binding:
                        if isinstance(binding[key], dict) and "value" in binding[key]:
                            values.add(binding[key]["value"])
    
    return values

def extract_values_from_llm(question_entry):
    """Extracts all 'value' URIs from the LLM-derived SPARQL response."""
    values = set()
    
    if "llm_derived_SPARQL_response" in question_entry:
        for result in question_entry["llm_derived_SPARQL_response"]:
            for key in result:
                values.add(result[key])  # Directly extract values
                
    return values

def verify_sparql_results(input_json, output_json):
    """Compares original answers with LLM-derived SPARQL results and adds 'is_correct' field."""
    # Load dataset
    with open(input_json, "r", encoding="utf-8") as file:
        original_data = json.load(file)

    with open(output_json, "r", encoding="utf-8") as file:
        llm_data = json.load(file)

    # Ensure correct structure
    if not isinstance(original_data, dict) or "questions" not in original_data:
        print("❌ ERROR: JSON format incorrect, expected a dictionary with a 'questions' key.")
        sys.exit(1)

    if not isinstance(llm_data, dict) or "questions" not in llm_data:
        print("❌ ERROR: JSON format incorrect in LLM dataset, expected a dictionary with a 'questions' key.")
        sys.exit(1)

    original_questions = {q["id"]: q for q in original_data["questions"]}
    llm_questions = {q["id"]: q for q in llm_data["questions"]}

    for question_id, llm_entry in llm_questions.items():
        if question_id in original_questions:
            original_values = extract_values_from_answers(original_questions[question_id])
            llm_values = extract_values_from_llm(llm_entry)

            # Compare sets
            llm_entry["is_correct"] = original_values == llm_values

            print(f"✅ Question ID {question_id} - Correct: {llm_entry['is_correct']}")
        else:
            print(f"⚠️ WARNING: Question ID {question_id} not found in original dataset.")

    # Save updated JSON
    with open(output_json, "w", encoding="utf-8") as file:
        json.dump(llm_data, file, indent=4, ensure_ascii=False)

    print(f"✅ Verification completed! Updated JSON saved to: {output_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify LLM-generated SPARQL responses against original dataset.")
    parser.add_argument("--input_json", type=str, required=True, help="Path to JSON file containing original dataset answers.")
    parser.add_argument("--output_json", type=str, required=True, help="Path to JSON file containing LLM responses (to be updated).")

    args = parser.parse_args()

    print(f"🔍 Input JSON (Original): {args.input_json}")
    print(f"📂 Output JSON (LLM Results): {args.output_json}")

    verify_sparql_results(args.input_json, args.output_json)
