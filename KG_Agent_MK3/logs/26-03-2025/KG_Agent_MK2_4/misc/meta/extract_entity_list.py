import json
import argparse
import re
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
    return [name.strip() for name in entity_names if name]  # Return cleaned list

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

def transform_json(input_file, output_file, api_key, num_questions, model, llm_provider, is_local_graph):
    """
    Transforms the input JSON structure into a simplified list of question-answer pairs,
    including extracted entity IDs from SPARQL, LLM, and Wikidata SPARQL endpoint,
    while preserving the original question ID.
    """
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Ensure data is a dictionary
    if not isinstance(data, dict) or "questions" not in data:
        raise ValueError("Invalid JSON structure: expected a dictionary with a 'questions' key.")

    questions_list = data["questions"]

    # Determine how many questions to process
    if num_questions is None or num_questions > len(questions_list):
        num_questions = len(questions_list)  # Process all questions if `num_questions` is not set

    transformed_data = []

    for entry in questions_list[:num_questions]:  # Process only `num_questions` questions
        # Use the original ID from the dataset
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
            
            # Append to transformed structure
            transformed_data.append({
                "id": original_id,  # Keep the original ID
                "question_text": question_text,  # The natural language question
                "sparql_query": sparql_query,  # The original SPARQL query from the dataset
                "llm_extracted_entity_names": "Local Graph, no entity extraction needed",  # Named entities extracted by the LLM
                "wikidata_entities_resolved": "Local Graph, no entity resolving needed"  # Wikidata Q-IDs mapped to LLM-extracted names
            })
        else:
            llm_extracted_entities = extract_entities_with_llm(question_text, api_key, model, llm_provider)

            # Query Wikidata to get entity IDs for all extracted names
            wikidata_entities_resolved = get_wikidata_entities(llm_extracted_entities)

            # Append to transformed structure
            transformed_data.append({
                "id": original_id,  # Keep the original ID
                "question_text": question_text,  # The natural language question
                "sparql_query": sparql_query,  # The original SPARQL query from the dataset
                "llm_extracted_entity_names": llm_extracted_entities,  # Named entities extracted by the LLM
                "wikidata_entities_resolved": wikidata_entities_resolved  # Wikidata Q-IDs mapped to LLM-extracted names
            })

        print(f"✅ Processed ID {original_id}")

    # Save to output JSON file
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(transformed_data, file, indent=4, ensure_ascii=False)

    print(f"✅ Transformed JSON saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Transform a JSON file into a simplified question-answer format with extracted entities.")
    parser.add_argument("--input_file", type=str, required=True, help="Path to the input JSON file.")
    parser.add_argument("--output_file", type=str, required=True, help="Path to save the transformed JSON output.")
    parser.add_argument("--api_key", type=str, required=True, help="API key for entity extraction.")
    parser.add_argument("--num_questions", type=int, help="Number of questions to process. If omitted, all questions will be processed.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model used for entity extraction.")
    parser.add_argument("--llm_provider", type=str, default="openai", help="Define which llm to use.")
    parser.add_argument("--is_local_graph", type=bool, required=True, help="Set True or False.")

    args = parser.parse_args()
    
    # Handle `num_questions`: Convert to `None` if empty or the string "None"
    if args.num_questions in (None, "", "None"):
        args.num_questions = None

    # Ensure `num_questions` is a positive integer if provided
    if args.num_questions is not None and args.num_questions <= 0:
        raise ValueError("Error: --num_questions must be a positive integer.")

    print(f"📌 Using num_questions: {args.num_questions}")

    # Call your processing function
    transform_json(args.input_file, args.output_file, args.api_key, args.num_questions, args.model, args.llm_provider, args.is_local_graph)

if __name__ == "__main__":
    main()
