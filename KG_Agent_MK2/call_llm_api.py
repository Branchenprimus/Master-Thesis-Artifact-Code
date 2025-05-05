import argparse
import os
import json
import sys
from openai import OpenAI
import time
from rdflib import Graph
from utility import Utils

def read_file(file_path):
    """Reads content from a file and returns it as a string."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        sys.stderr.write(f"WARNING: Could not read file {file_path}: {e}\n")
        return ""

def call_llm(full_prompt, max_tokens, temperature, api_key, model, llm_provider):
    """Calls OpenAI's GPT model via the ChatGPT API or DeepSeek API."""
    
    client = OpenAI(api_key=api_key, base_url=Utils.resolve_llm_provider(llm_provider))
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a SPARQL expert. Only output valid SPARQL queries."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )

        return completion.choices[0].message.content.strip()
    
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: API call to ChatGPT failed: {e}\n")
        sys.exit(1)


def process_json_and_shapes(json_path, shape_dir, system_prompt_path, api_key, model, max_tokens, initial_temperature,
                            llm_provider, is_local_graph, max_retries, sparql_endpoint_url, local_graph_path, shape_type, dataset_type, baseline_run, system_prompt_path_baseline_run):
    """Iterates over JSON questions and shape files to generate SPARQL queries, ensuring only one LLM call per question."""

    # Load the JSON file with questions
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    print(f"🔍 Debug: Starting to process {len(data)} questions.")

    if baseline_run:
        system_prompt_path = system_prompt_path_baseline_run
    # Read system prompt
    system_prompt = read_file(system_prompt_path)

    if is_local_graph and not baseline_run:
        local_shape_file_path = os.path.join(shape_dir, f"local_graph_shape.{shape_type}")
        if not os.path.exists(local_shape_file_path):
            raise FileNotFoundError(f"❌ ERROR: Local graph shape file not found: {local_shape_file_path}")
        local_shape_data = read_file(local_shape_file_path)

    for entry in data:
        if not isinstance(entry, dict):
            print(f"⚠️ Skipping non-dict entry: {entry}")
            continue

        question_id = entry.get('baseline_id')
        question = entry.get("baseline_question_text", "").strip()

        print(f"\n🔎 Processing question ID {question_id}")
        print(f"   ↳ Question: {repr(question)}")
        print(f"   ↳ Baseline SPARQL query: {repr(entry.get('baseline_sparql_query'))}")
        if not baseline_run:
            print(f"   ↳ Resolved entities: {repr(entry.get('endpoint_entities_resolved'))}")
        else:
            print(f"   ↳ Resolved entities: ⚠️ \"baseline_run:\" {baseline_run}")

        if not question:
            print(f"⚠️ Skipping question ID {question_id} due to missing question text.")
            continue

        if is_local_graph and not baseline_run:
            merged_shape_data = local_shape_data
        elif not is_local_graph and not baseline_run:
            entity_dict = entry.get("endpoint_entities_resolved", {})
            if not isinstance(entity_dict, dict) or not entity_dict:
                print(f"⚠️ Skipping question ID {question_id} due to missing or invalid entity_dict.")
                continue

            shape_file_path = os.path.join(shape_dir, f"question_{question_id}_shape.{shape_type}")
            if not os.path.exists(shape_file_path):
                print(f"⚠️ Shape file missing: {shape_file_path}")
                continue

            merged_shape_data = read_file(shape_file_path)

        retries = 0
        final_query = None
        result = None
        temperature = initial_temperature
        previous_response = None
        attempts_log = []  # Change from dictionary to list

        print(f"🔄 Constructing SPARQL with retry limit = {max_retries}")

        while retries <= max_retries:
            if previous_response and not baseline_run:
                full_prompt = (
                    system_prompt.replace("{nlq}", question)
                    .replace("{ont}", dataset_type)
                    .replace("{shp_typ}", shape_type)
                    .replace("{shp_dat}", merged_shape_data)
                    + f"\n\n### Previous attempt (failed):\n{previous_response}\n\n### Revised SPARQL Query:\n```sparql"
                )
            elif previous_response and baseline_run:
                full_prompt = (
                    system_prompt.replace("{nlq}", question)
                    .replace("{ont}", dataset_type)
                    + f"\n\n### Previous attempt (failed):\n{previous_response}\n\n### Revised SPARQL Query:\n```sparql"
                )
                
            elif not previous_response and not baseline_run:
                full_prompt = (system_prompt.replace("{nlq}", question)
                    .replace("{ont}", dataset_type)
                    .replace("{shp_typ}", shape_type)
                    .replace("{shp_dat}", merged_shape_data)
                )
            elif not previous_response and baseline_run:
                full_prompt = (system_prompt.replace("{nlq}", question)
                    .replace("{ont}", dataset_type)
                )
            temperature = round(min(initial_temperature + 0.1 * retries, 2), 2)  # capped at 2.0
            print(f"🔄 Attempt {retries + 1}/{max_retries + 1} with temperature: {temperature}")
            response = call_llm(full_prompt, max_tokens, temperature, api_key, model, llm_provider)

            if not response:
                retries += 1
                time.sleep(1)
                continue

            final_query = response.replace("```sparql\n", "").replace("\n```", "").strip()
            print(f"##########################################\nFull prompt: {full_prompt}\n##########################################")

            print(f"LLM generated SPARQL query:\n{final_query}")
            
            if is_local_graph:
                llm_generated_result = Utils.query_local_graph(final_query, local_graph_path)

            else:
                llm_generated_result = Utils.query_sparql_endpoint(final_query, sparql_endpoint_url)

            # Truncate results if they exceed 10000 and mark as failed
            if isinstance(llm_generated_result, list) and len(llm_generated_result) > 10000:
                print(f"⚠️ Result exceeds 10000 entries. Truncating and marking as failed.")
                llm_generated_result = []
                failed = True
                failure_reason = "Result exceeded 10000 entries (truncated)"
            else:
                failed = Utils.is_faulty_result(llm_generated_result)
                failure_reason = "Faulty result" if failed else None

            attempts_log.append({
                "attempt": retries + 1,
                "temperature": temperature,
                "query": final_query,
                "result": llm_generated_result,
                "failed": str(failed),
                "reason": failure_reason if failure_reason else "None"
            })

            if failure_reason:
                print(f"⚠️ Failure reason: {failure_reason}")

            if not failed:
                print(f"✅ SPARQL executed successfully for question ID {question_id}")
                break
            else:
                print(f"⚠️ Faulty result. Retrying... ({retries + 1}/{max_retries})")
                previous_response = f"Query: {final_query}\nResult: {result}"
                retries += 1
                time.sleep(1)

        entry["LLM_generated_sparql_query"] = attempts_log
        entry["sparql_comparison_result"] = {
            "is_correct": "",
            "llm_failed_attempts": retries
        }

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print(f"\n🎉 Done. All questions processed and saved to: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate SPARQL queries from an LLM for a dataset.")
    parser.add_argument("--json_path", required=True)
    parser.add_argument("--system_prompt_path", required=True)
    parser.add_argument("--shape_path", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--max_tokens", default=512, type=int)
    parser.add_argument("--temperature", default=0.1, type=float)
    parser.add_argument("--llm_provider", type=str, default="openai")
    parser.add_argument('--is_local_graph', type=Utils.str_to_bool, required=True, help="Use local graph (True/False)")
    parser.add_argument("--max_retries", type=int, default=2)
    parser.add_argument("--sparql_endpoint_url", type=str)
    parser.add_argument("--local_graph_path", type=str)
    parser.add_argument("--shape_type", type=str)
    parser.add_argument("--dataset_type", type=str, default="default", help="Type of dataset to process.")
    parser.add_argument("--baseline_run", type=Utils.str_to_bool, default=False, help="Run baseline SPARQL queries.")
    parser.add_argument("--system_prompt_path_baseline_run", type=str, default="system_prompt_baseline_run.txt", help="Path to the system prompt for baseline run.")

    args = parser.parse_args()
    print(f"⚠️ baseline_run: {args.baseline_run}")
    if args.is_local_graph and not args.local_graph_path:
        parser.error("--local_graph_path is required when --is_local_graph is True.")
    if not args.is_local_graph and not args.sparql_endpoint_url:
        parser.error("--sparql_endpoint_url is required when --is_local_graph is False.")

    process_json_and_shapes(
        json_path=args.json_path,
        shape_dir=args.shape_path,
        system_prompt_path=args.system_prompt_path,
        api_key=args.api_key,
        model=args.model,
        max_tokens=args.max_tokens,
        initial_temperature=args.temperature,
        llm_provider=args.llm_provider,
        is_local_graph=args.is_local_graph,
        max_retries=args.max_retries,
        sparql_endpoint_url=args.sparql_endpoint_url,
        local_graph_path=args.local_graph_path,
        shape_type=args.shape_type,
        dataset_type=args.dataset_type,
        baseline_run=args.baseline_run,
        system_prompt_path_baseline_run=args.system_prompt_path_baseline_run
    )
    print("🔍 Debug: process_json_and_shapes executed successfully.")

if __name__ == "__main__":
    main()
