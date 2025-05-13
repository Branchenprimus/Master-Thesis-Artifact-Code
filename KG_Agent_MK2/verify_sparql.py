import json
import argparse
import time
import math
from utility import Utils

def compare_sparql_results(entry):
    """Compares baseline and LLM-generated SPARQL query responses using TP/FP/FN classification."""
    question_id = entry.get("baseline_id", "unknown")

    baseline_entities = set(entry.get("baseline_sparql_query_response", []))
    llm_queries = entry.get("LLM_generated_sparql_query", [])
    llm_entities = set(llm_queries[-1]["result"]) if llm_queries else set()

    # Log preview
    print(f"First 5 baseline_entities: {list(baseline_entities)[:5] if baseline_entities else 'None'}")
    print(f"First 5 llm_entities: {list(llm_entities)[:5] if llm_entities else 'None'}")

    # Case: no valid baseline -> skip
    if not baseline_entities:
        classification = "Invalid"

    # Case: TP = exact match
    elif baseline_entities == llm_entities:
        classification = "TP"

    # Case: FN = baseline has values but LLM is empty/null
    elif not llm_entities or all(str(e).strip() in {"", "0", "0.0", "null", "None"} for e in llm_entities):
        classification = "FN"

    # Case: FP = LLM returned something incorrect
    else:
        classification = "FP"

    print(f"Question ID: {question_id}")
    print(f"Classification: {classification}")

    return classification


def count_total_tokens(data):
    """Sums prompt, completion, total tokens, and retry count across all questions."""
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_retries = 0
    total_questions = len(data)

    for entry in data:
        comparison = entry.get("sparql_comparison_result", {})
        total_prompt_tokens += int(comparison.get("prompt_tokens_by_question", 0))
        total_completion_tokens += int(comparison.get("completion_tokens_by_question", 0))
        total_tokens += int(comparison.get("total_tokens_by_question", 0))
        total_retries += int(comparison.get("llm_failed_attempts", 0))

    avg_retries_per_question = total_retries / total_questions if total_questions else 0

    print("\n📊 Token Usage Summary")
    print(f"🔹 Prompt Tokens:     {total_prompt_tokens}")
    print(f"🔹 Completion Tokens: {total_completion_tokens}")
    print(f"🔹 Total Tokens:      {total_tokens}")
    print(f"🔁 Total Retries: {total_retries}")
    print(f"🔁 Avg. Retries per Question:      {avg_retries_per_question:.2f}")

    return {
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "total_retries": total_retries,
        "avg_retries_per_question": avg_retries_per_question
    }

def compute_effort_normalized_accuracy(execution_accuracy, token_summary, total_questions):
    avg_retries = token_summary["avg_retries_per_question"]
    avg_tokens = token_summary["total_tokens"] / total_questions if total_questions else 0

    ena = (
        execution_accuracy / ((1 + avg_retries) * math.log10(1 + avg_tokens))
        if avg_tokens > 0 else 0
    )
    return ena

def process_json(json_path, sparql_endpoint_url, is_local_graph, local_graph_location, num_questions, max_retries, log_dir, llm_provider_sparql_generation, llm_provider_entity_extraction, model_entity_extraction, model_sparql_generation, benchmark_dataset, shape_type, dataset_type, annotation, baseline_run, run_index):
    """Processes the JSON file, compares SPARQL query results, and appends the comparison results to the JSON file."""

    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    tp = 0
    fp = 0
    fn = 0
    invalid = 0

    for entry in data:
        question_id = entry.get("baseline_id", "unknown")

        # Baseline SPARQL query
        baseline_query = entry.get("baseline_sparql_query")
        baseline_question_text = entry.get("baseline_question_text")
        print(f"\nbaseline_question_text: {baseline_question_text}")
        print(f"baseline_sparql_query: {baseline_query}")

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
        classification = compare_sparql_results(entry)

        # Ensure nested dict exists before assigning
        if "sparql_comparison_result" not in entry:
            entry["sparql_comparison_result"] = {}

        entry["sparql_comparison_result"]["is_correct"] = classification


        if classification == "TP":
            tp += 1
        elif classification == "FP":
            fp += 1
        elif classification == "FN":
            fn += 1
        elif classification == "Invalid":
            invalid += 1
        
        # Optional sleep to avoid overloading endpoint
        time.sleep(1)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # Final accuracy and output
    execution_accuracy = (tp * 100)/ (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0

    # Count token usage
    token_summary = count_total_tokens(data)

    ena_score = compute_effort_normalized_accuracy(execution_accuracy, token_summary, len(data))

    # Save everything to a summary.txt file
    summary_path = json_path.replace(".json", "_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("==== SPARQL Evaluation Summary ====\n\n")
        f.write(f"LLM Provider for SPARQL Generation:   {llm_provider_sparql_generation}\n")
        f.write(f"LLM Provider for Entity Extraction:   {llm_provider_entity_extraction}\n")
        f.write(f"Model for Entity Extraction:          {model_entity_extraction}\n")
        f.write(f"Model for SPARQL Generation:          {model_sparql_generation}\n")
        f.write(f"Benchmark Dataset:                    {benchmark_dataset}\n")
        f.write(f"Shape Type:                           {shape_type}\n")
        f.write(f"Dataset Type:                         {dataset_type}\n")
        f.write(f"Annotation:                           {annotation}\n")
        f.write(f"Baseline Run:                         {baseline_run}\n")
        f.write(f"SPARQL Endpoint URL:                  {sparql_endpoint_url}\n")
        f.write(f"Local Graph Location:                 {local_graph_location}\n")
        f.write(f"Number of Questions:                  {num_questions}\n")
        f.write(f"Max Retries:                          {max_retries}\n")
        f.write(f"Log Directory:                        {log_dir}\n")
        f.write(f"ID:                                   {run_index}\n\n")
        f.write("==== Token Usage ====\n\n")
        f.write(f"Total Prompt Tokens:                  {token_summary['prompt_tokens']}\n")
        f.write(f"Total Completion Tokens:              {token_summary['completion_tokens']}\n")
        f.write(f"Total Tokens:                         {token_summary['total_tokens']}\n\n")
        f.write(f"Average Prompt Tokens per Q:          {token_summary['prompt_tokens']/len(data):.2f}\n")
        f.write(f"Average Completion Tokens per Q:      {token_summary['completion_tokens']/len(data):.2f}\n")
        f.write(f"Average Total Tokens per Q:           {token_summary['total_tokens']/len(data):.2f}\n\n")
        f.write("==== Simple Metrics ====\n\n")
        f.write(f"Total Retries:                        {token_summary['total_retries']}\n")
        f.write(f"Avg. Retries per Q:                   {token_summary['avg_retries_per_question']:.2f}\n\n")
        f.write(f"True Positives (TP):                  {tp}\n")
        f.write(f"False Positives (FP):                 {fp}\n")
        f.write(f"False Negatives (FN):                 {fn}\n")
        f.write(f"Invalid Baseline Entries:             {invalid}\n\n")
        f.write("==== Advanced Metrics ====\n\n")
        f.write(f"Precision:                            {precision:.2f}\n")
        f.write(f"Recall:                               {recall:.2f}\n")
        f.write(f"F1-score:                             {f1_score:.2f}\n")
        f.write(f"Execution Accuracy (TP rate):         {execution_accuracy:.2f}\n")
        f.write(f"Effort-Normalized Accuracy (ENA):     {ena_score:.2f}\n")



    print(f"\n📊 Execution Accuracy: {execution_accuracy:.2f}")
    print(f"📝 Summary written to: {summary_path}")

    # Save updated dataset
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"✅ All queries executed and results saved to {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare SPARQL query results using entity overlap.")
    parser.add_argument("--json_path", type=str, required=True, help="Path to the JSON file with SPARQL query responses.")
    parser.add_argument("--sparql_endpoint_url", type=str, help="SPARQL endpoint URL (ignored if --is_local_graph is used).")
    parser.add_argument("--is_local_graph", type=Utils.str_to_bool, required=True, help="Set True or False.")
    parser.add_argument("--local_graph_location", type=str, help="Path to the local RDF graph file (e.g., .ttl, .rdf).")
    parser.add_argument("--num_questions", type=int, help="Number of questions to process.")
    parser.add_argument("--max_retries", type=int, help="Maximum number of consecutive retries.")
    parser.add_argument("--log_dir", type=str, help="Directory to store logs.")
    parser.add_argument("--llm_provider_sparql_generation", type=str, help="LLM provider for SPARQL generation.")
    parser.add_argument("--llm_provider_entity_extraction", type=str, help="LLM provider for entity extraction.")
    parser.add_argument("--model_entity_extraction", type=str, help="Model used for entity extraction.")
    parser.add_argument("--model_sparql_generation", type=str, help="Model used for SPARQL generation.")
    parser.add_argument("--benchmark_dataset", type=str, help="Benchmark dataset to use.")
    parser.add_argument("--shape_type", type=str, help="Shape type for the dataset.")
    parser.add_argument("--dataset_type", type=str, help="Type of dataset being processed.")
    parser.add_argument("--annotation", type=str, help="Annotation type for the dataset.")
    parser.add_argument("--baseline_run", type=Utils.str_to_bool, help="Indicates if this is a baseline run.")
    parser.add_argument("--run_index", type=str, help="Run ID for the current execution.")

    args = parser.parse_args()
    
    process_json(args.json_path, args.sparql_endpoint_url, args.is_local_graph, args.local_graph_location, args.num_questions, args.max_retries, args.log_dir, args.llm_provider_sparql_generation, args.llm_provider_entity_extraction, args.model_entity_extraction, args.model_sparql_generation, args.benchmark_dataset, args.shape_type, args.dataset_type, args.annotation, args.baseline_run, args.run_index)
