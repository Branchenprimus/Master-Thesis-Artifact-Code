import json
import argparse
import requests
import openai

def extract_entities_with_llm(nlq, api_key, model, llm_provider):
    """
    Uses an LLM to extract the most relevant entities from a natural language query.
    Returns a list of entities.
    """
    
    if llm_provider == "openai":
        client = openai.OpenAI(api_key=api_key)
    elif llm_provider == "deepseek":
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1", 
        )

    prompt = f"""Extract the most relevant named wikidata entities from the following question:
    
    Question: "{nlq}"
    
    Return a comma-separated list of entity names without explanations. Think rationally and in context of the question but respond only with entities literally named in the question. Extracted entities should be in singular form.
    """

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are an expert in extracting named entities from questions."},
                  {"role": "user", "content": prompt}],
        max_tokens=50,
        temperature=0.2
    )
    
    print(f"LLM response: {response}")

    entity_names = response.choices[0].message.content.strip().split(", ")
    return [name.strip() for name in entity_names if name]

def get_wikidata_entities(entity_names):
    """Resolves entity names to Wikidata Q-IDs."""
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
                wikidata_entities[entity_name] = results[0]["entity"]["value"].split("/")[-1]
    return wikidata_entities

def transform_json(input_file, output_file, api_key, model, llm_provider, is_local_graph, question_index):
    """Processes a single question specified by index."""
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or "questions" not in data:
        raise ValueError("Invalid JSON structure: expected a dictionary with a 'questions' key.")

    questions_list = data["questions"]
    
    # Validate question index
    if question_index < 0 or question_index >= len(questions_list):
        raise ValueError(f"Question index {question_index} is out of range (total questions: {len(questions_list)}).")

    entry = questions_list[question_index]
    transformed_data = []

    original_id = entry.get("id")
    question_text = next(
        (q["string"] for q in entry["question"] if q["language"] == "en"),
        entry["question"][0]["string"]
    )
    sparql_query = entry["query"]["sparql"]

    if is_local_graph:
        transformed_data.append({
            "id": original_id,
            "question_text": question_text,
            "sparql_query": sparql_query,
            "llm_extracted_entity_names": "Local Graph, no entity extraction needed",
            "wikidata_entities_resolved": "Local Graph, no entity resolving needed"
        })
    else:
        llm_extracted_entities = extract_entities_with_llm(question_text, api_key, model, llm_provider)
        wikidata_entities_resolved = get_wikidata_entities(llm_extracted_entities)
        transformed_data.append({
            "id": original_id,
            "question_text": question_text,
            "sparql_query": sparql_query,
            "llm_extracted_entity_names": llm_extracted_entities,
            "wikidata_entities_resolved": wikidata_entities_resolved
        })

    print(f"✅ Processed ID {original_id} (Index: {question_index})")

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(transformed_data, file, indent=4, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="Process a single question from a JSON file using an index.")
    parser.add_argument("--input_file", type=str, required=True, help="Path to the input JSON file.")
    parser.add_argument("--output_file", type=str, required=True, help="Path to save the output JSON.")
    parser.add_argument("--api_key", type=str, required=True, help="API key for entity extraction.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model used for entity extraction.")
    parser.add_argument("--llm_provider", type=str, default="openai", help="LLM provider (openai/deepseek).")
    parser.add_argument("--is_local_graph", type=bool, required=True, help="True for local graph, False otherwise.")
    parser.add_argument("--question_index", type=int, required=True, help="0-based index of the question to process.")

    args = parser.parse_args()
    
    transform_json(
        args.input_file,
        args.output_file,
        args.api_key,
        args.model,
        args.llm_provider,
        args.is_local_graph,
        args.question_index
    )

if __name__ == "__main__":
    main()
