#!/usr/bin/env python3
import json
import argparse
import sys
import os

def extract_original_answers(question_entry):
    """Extracts answer URIs from the original dataset's 'answers' field."""
    original_answers = set()

    if "answers" in question_entry:
        for answer_set in question_entry["answers"]:
            if "results" in answer_set and "bindings" in answer_set["results"]:
                for binding in answer_set["results"]["bindings"]:
                    for key in binding:
                        if "value" in binding[key]:
                            original_answers.add(binding[key]["value"])

    return original_answers

def extract_llm_answers(question_entry):
    """Extracts answer URIs from the LLM-derived SPARQL response."""
    llm_answers = set()

    if "llm_derived_SPARQL_response" in question_entry:
        for result in question_entry["llm_derived_SPARQL_response"]:
            for key in result:
                llm_answers.add(result[key])  # Directly add values

    return llm_answers

def verify_sparql_results(input_json, output_json):
    """Compares original answers with LLM-derived SPARQL results and adds 'is_correct' field."""
    # Load dataset
    with open(input_json, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Ensure data has the correct structure
    if not isinstance(data, dict) or "questions" not in data or not isinstance(data["questions"], list):
        print("❌ ERROR: JSON format incorrect, expected a dictionary with a 'questions' key containing a list.")
        sys.exit(1)

    for entry in data["questions"]:  # Accessing questions inside the dictionary
        original_answers = extract_original_answers(entry)
        llm_answers = extract_llm_answers(entry)

        # Compare sets of answers
        entry["is_correct"] = original_answers == llm_answers

        print(f"✅ Question ID {entry['id']} - Correct: {entry['is_correct']}")

    # Save updated JSON
    with open(output_json, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"✅ Verification completed! Updated JSON saved to: {output_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify LLM-generated SPARQL responses against original dataset.")
    parser.add_argument("--input_json", type=str, required=True, help="Path to JSON file containing LLM responses and original answers.")
    parser.add_argument("--output_json", type=str, required=True, help="Path to save the verified JSON output.")

    args = parser.parse_args()

    print(f"🔍 Input JSON: {args.input_json}")
    print(f"📂 Output JSON: {args.output_json}")

    verify_sparql_results(args.input_json, args.output_json)
