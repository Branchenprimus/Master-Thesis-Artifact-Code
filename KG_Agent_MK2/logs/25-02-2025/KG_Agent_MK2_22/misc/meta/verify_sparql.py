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
                    for key in binding:  # Extract all values dynamically
                        if isinstance(binding[key], dict) and "value" in binding[key]:
                            values.add(binding[key]["value"])

    return values

def extract_values_from_llm(question_entry):
    """Extracts all 'value' URIs from the LLM-derived SPARQL response."""
    values = set()

    if "llm_derived_SPARQL_response" in question_entry:
        for result in question_entry["llm_derived_SPARQL_response"]:
            for key in result:  # Extract all values dynamically, ignoring key names
                values.add(result[key])

    return values

def verify_sparql_results(input_json, output_json):
    """Compares original answers with LLM-derived SPARQL results and adds 'is_correct' field."""
    # Load original dataset
    with open(input_json, "r", encoding="utf-8") as file:
        original_data = json.load(file)

    # Load LLM-generated dataset
    with open(output_json, "r", encoding="utf-8") as file:
        llm_data = json.load(file)

    # Ensure original dataset is a dictionary with "questions"
    if not isinstance(original_data, dict) or "questions" not in original_data:
        print("❌ ERROR: JSON format incorrect in the original dataset, expected a dictionary with a 'questions' key.")
        sys.exit(1)

    # Ensure LLM-generated dataset is a list
    if not isinstance(llm_data, list):
        print("❌ ERROR: JSON format incorrect in LLM dataset, expected a list.")
        sys.exit(1)

    original_questions = {str(q["id"]): q for q in original_data["questions"]}
    llm_questions = {str(q["id"]): q for q in llm_data}

    correct_count = 0
    incorrect_count = 0

    for question_id, llm_entry in llm_questions.items():
        if question_id in original_questions:
            original_values = extract_values_from_answers(original_questions[question_id])
            llm_values = extract_values_from_llm(llm_entry)

            print(f"🔍 Question ID {question_id}")
            print(f"📌 Original Values: {original_values}")
            print(f"📌 LLM Values: {llm_values}")

            # Compare sets of answers
            llm_entry["is_correct"] = original_values == llm_values

            if llm_entry["is_correct"]:
                correct_count += 1
            else:
                incorrect_count += 1

            print(f"✅ Question ID {question_id} - Correct: {llm_entry['is_correct']}")
        else:
            print(f"⚠️ WARNING: Question ID {question_id} not found in the original dataset.")

    # Save updated JSON
    with open(output_json, "w", encoding="utf-8") as file:
        json.dump(llm_data, file, indent=4, ensure_ascii=False)

    # Compute total and quota
    total_count = correct_count + incorrect_count
    success_rate = (correct_count / total_count * 100) if total_count > 0 else 0

    # Print statistics
    print("\n📊 ===== Verification Statistics =====")
    print(f"✅ Correct SPARQL Queries: {correct_count}")
    print(f"❌ Incorrect SPARQL Queries: {incorrect_count}")
    print(f"📈 Accuracy: {success_rate:.2f}%")
    print("=====================================\n")

    print(f"✅ Verification completed! Updated JSON saved to: {output_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify LLM-generated SPARQL responses against original dataset.")
    parser.add_argument("--input_json", type=str, required=True, help="Path to JSON file containing original dataset answers.")
    parser.add_argument("--output_json", type=str, required=True, help="Path to JSON file containing LLM responses (to be updated).")

    args = parser.parse_args()

    print(f"🔍 Input JSON (Original): {args.input_json}")
    print(f"📂 Output JSON (LLM Results): {args.output_json}")

    verify_sparql_results(args.input_json, args.output_json)
