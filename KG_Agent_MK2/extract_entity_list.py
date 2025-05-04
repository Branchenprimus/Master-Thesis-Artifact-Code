import json
import argparse
import traceback
import sys
from openai import OpenAI
import requests
from utility import Utils

def extract_entities_with_llm(nlq, api_key, model, llm_provider, system_prompt_path, max_tokens, temperature, dataset_type):
    """
    Uses an LLM to extract the most relevant entities from a natural language query.
    Replaces {nlq} in the prompt file with the current question.
    Returns a list of entity names.
    """
    # Load prompt template
    with open(system_prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Inject question into template
    user_prompt = prompt_template.replace("{nlq}", nlq).replace("{ont}", dataset_type)
    
    # Select provider
    client = OpenAI(api_key=api_key, base_url=Utils.resolve_llm_provider(llm_provider))

    # Call LLM
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert in extracting named entities from questions."},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )

    # Parse and return entity names
    entity_names = response.choices[0].message.content.strip().split(",")
    
    return [name.strip() for name in entity_names if name.strip()]


def get_wikidata_entities(entity_names):
    """
    Queries Wikidata to get the entity IDs (Q-numbers) for multiple entity names.
    Returns a dictionary mapping names to Q-IDs.
    """
    wikidata_entities = {}

    for entity_name in entity_names:
        sparql_query = f"""
        SELECT ?entity WHERE {{
            ?entity rdfs:label "{entity_name}"@en .
        }}
        LIMIT 1
        """

        url = "https://query.wikidata.org/sparql"
        headers = {"User-Agent": "EntityExtractorBot/1.0"}
        response = requests.get(url, params={"query": sparql_query, "format": "json"}, headers=headers)

        if response.status_code == 200:
            results = response.json().get("results", {}).get("bindings", [])
            if results:
                wikidata_entities[entity_name] = results[0]["entity"]["value"].split("/")[-1]  # Extract Q-ID

    return wikidata_entities

def get_dbpedia_entities(entity_names):
    """
    Queries DBpedia to get the entity IDs (DBpedia URIs) for multiple entity names.
    Returns a dictionary mapping names to DBpedia URIs.
    Logs errors and warnings to stderr.
    """
    dbpedia_entities = {}
    url = "http://dbpedia.org/sparql"
    headers = {"User-Agent": "EntityExtractorBot/1.0"}

    for entity_name in entity_names:
        sparql_query = f"""
        SELECT ?entity WHERE {{
            ?entity rdfs:label "{entity_name}"@en .
        }}
        LIMIT 1
        """

        try:
            response = requests.get(
                url,
                params={"query": sparql_query, "format": "json"},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200 and response.text.strip():
                results = response.json().get("results", {}).get("bindings", [])
                if results:
                    dbpedia_entities[entity_name] = results[0]["entity"]["value"]
                else:
                    print(f"🔍 No DBpedia match found for '{entity_name}'", file=sys.stderr)
            else:
                print(f"⚠️ Bad response for '{entity_name}'", file=sys.stderr)
                print(f"  → Status: {response.status_code} {response.reason}", file=sys.stderr)
                print(f"  → URL: {response.url}", file=sys.stderr)
                print(f"  → Headers: {dict(response.headers)}", file=sys.stderr)
                if response.text.strip():
                    print(f"  → Body (first 500 chars):\n{response.text.strip()[:500]}", file=sys.stderr)
                else:
                    print(f"  → Body is empty", file=sys.stderr)

        except Exception as e:
            print("❌ Exception during DBpedia entity lookup:", file=sys.stderr)
            print(f"Entity name: '{entity_name}'", file=sys.stderr)
            print(f"SPARQL query:\n{sparql_query.strip()}", file=sys.stderr)
            print(f"Exception message: {e}", file=sys.stderr)
            print("Full traceback:", file=sys.stderr)
            traceback.print_exc()

    return dbpedia_entities



def transform_json(benchmark_dataset, output_file, api_key, num_questions, model, llm_provider, is_local_graph, system_prompt_path, max_tokens, temperature, dataset_type):
    """
    Transforms the input JSON structure into a simplified list of question-answer pairs,
    including extracted entity IDs from SPARQL, LLM, and Wikidata SPARQL endpoint,
    while preserving the original question ID.
    """
    try:
        with open(benchmark_dataset, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {benchmark_dataset}. Error: {e}")

    if isinstance(data, dict) and "questions" in data:
        questions_list = data["questions"]
    elif isinstance(data, list):
        questions_list = data
    else:
        raise ValueError(
            f"Invalid JSON structure in file {benchmark_dataset}: expected a list or a dictionary with a 'questions' key."
        )

    # Validate each question entry
    for entry in questions_list:
        if not isinstance(entry, dict):
            raise ValueError("Invalid question entry: each question must be a dictionary.")
        if "id" not in entry or "question" not in entry or "query" not in entry:
            raise ValueError("Invalid question entry: missing required keys ('id', 'question', 'query').")
        if not isinstance(entry["question"], list) or not entry["question"]:
            raise ValueError("Invalid question entry: 'question' must be a non-empty list.")
        if not isinstance(entry["query"], dict) or "sparql" not in entry["query"]:
            raise ValueError("Invalid question entry: 'query' must be a dictionary containing a 'sparql' key.")

    if num_questions is None or num_questions > len(questions_list):
        num_questions = len(questions_list)

    transformed_data = []

    for entry in questions_list[:num_questions]:  # Process only `num_questions` questions
        original_id = entry.get("id")

        # Get the English question (fallback to first available if no English)
        question_text = next(
            (q["string"] for q in entry["question"] if q["language"] == "en"),
            entry["question"][0]["string"]  # Fallback
        )

        # Get the SPARQL query
        sparql_query = entry["query"]["sparql"]

        # Extract multiple entities from NLQ using LLM
        if is_local_graph:
            transformed_data.append({
                "baseline_id": original_id,
                "baseline_question_text": question_text,
                "baseline_sparql_query": sparql_query,
                "llm_extracted_entity_names": "Local Graph, no entity extraction needed",
                "endpoint_entities_resolved": "Local Graph, no entity resolving needed"
            })
        else:
            llm_extracted_entities = extract_entities_with_llm(question_text, api_key, model, llm_provider, system_prompt_path, max_tokens, temperature, dataset_type)

            if dataset_type == "wikidata": 
                # Query Wikidata to get entity IDs for all extracted names
                endpoint_entities_resolved = get_wikidata_entities(llm_extracted_entities)
            elif dataset_type == "dbpedia":
                # Query DBpedia to get entity IDs for all extracted names
                endpoint_entities_resolved = get_dbpedia_entities(llm_extracted_entities)
                
            transformed_data.append({
                "baseline_id": original_id,
                "baseline_question_text": question_text,
                "baseline_sparql_query": sparql_query,
                "llm_extracted_entity_names": llm_extracted_entities,
                "endpoint_entities_resolved": endpoint_entities_resolved
            })

            print(f"✅ Processed ID {original_id}")
            print(f"baseline_question_text {question_text}")
            print(f"baseline_sparql_query {sparql_query}")
            print(f"llm_extracted_entity_names {llm_extracted_entities}")
            print(f"endpoint_entities_resolved {endpoint_entities_resolved}")
            print("-----------------------------------------------------")

    # Save to output JSON file
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(transformed_data, file, indent=4, ensure_ascii=False)

    print(f"✅ Transformed JSON saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Transform a JSON file into a simplified question-answer format with extracted entities.")
    parser.add_argument("--benchmark_dataset", type=str, required=True, help="Path to the input JSON file.")
    parser.add_argument("--output_file", type=str, required=True, help="Path to save the transformed JSON output.")
    parser.add_argument("--api_key", type=str, required=True, help="API key for entity extraction.")
    parser.add_argument("--num_questions", type=int, help="Number of questions to process.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model used for entity extraction.")
    parser.add_argument("--llm_provider", type=str, default="openai", help="Define which llm to use.")
    parser.add_argument("--max_tokens", default=50, type=int)
    parser.add_argument("--temperature", default=0.2, type=float)
    parser.add_argument("--is_local_graph", type=Utils.str_to_bool, required=True, help="Set True or False.")
    parser.add_argument("--system_prompt_path", required=True, help="Path to system prompt file.")
    parser.add_argument("--dataset_type", type=str, default="default", help="Type of dataset to process.")

    args = parser.parse_args()
    print(f"✅ is_local_graph: {args.is_local_graph}")

    if args.num_questions in (None, 0):
        num_questions = None  # Treat 0 as "process all questions"
    elif args.num_questions < 0:
        raise ValueError("Error: --num_questions must be zero or a positive integer.")
    else:
        num_questions = args.num_questions

    print(f"📌 Using num_questions: {'ALL' if num_questions is None else num_questions}")

    # Use the validated variable here
    transform_json(args.benchmark_dataset, args.output_file, args.api_key, num_questions, args.model, args.llm_provider, args.is_local_graph, args.system_prompt_path, args.max_tokens, args.temperature, args.dataset_type)

if __name__ == "__main__":
    main()
