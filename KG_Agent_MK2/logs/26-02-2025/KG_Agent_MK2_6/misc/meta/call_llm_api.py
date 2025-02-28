import argparse
import os
import json
import sys
from openai import OpenAI

def read_file(file_path):
    """Reads content from a file and returns it as a string."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        sys.stderr.write(f"WARNING: Could not read file {file_path}: {e}\n")
        return ""

def construct_prompt(system_prompt, user_prompt, shape_data):
    """Constructs a structured prompt ensuring the model outputs only SPARQL."""
    return f"""{system_prompt}

### User Query:
{user_prompt}

### Shape Constraints:
{shape_data}

### Expected SPARQL Query:
```sparql
"""

def call_llm(full_prompt, max_tokens, temperature, api_key, model, llm_switch):
    """Calls OpenAI's GPT model via the ChatGPT API or DeepSeek API."""
    
    if llm_switch == "chatgpt":
        client = openai.OpenAI(api_key=api_key)
    
    elif llm_switch == "deepseek":
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1", 
        )    

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
        print(f"Full prompt: {full_prompt}")
        print(f"ChatGPT completion object: {completion}")
        return completion.choices[0].message.content.strip()
    
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: API call to ChatGPT failed: {e}\n")
        sys.exit(1)

def save_response(output_dir, question_id, response):
    """Saves the LLM response to a file, ensuring only one response per question ID."""
    os.makedirs(output_dir, exist_ok=True)

    # Remove SPARQL code block formatting
    response = response.replace("```sparql", "").replace("```", "").strip()

    # Define the output file using the original question ID
    output_file = os.path.join(output_dir, f"question_{question_id}.sparql")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"✅ Response saved to {output_file}")
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: Failed to write output file: {e}\n")
        sys.exit(1)

def process_json_and_shapes(json_path, shape_dir, system_prompt_path, output_dir, api_key, model, max_tokens, temperature, llm_switch):
    """Iterates over JSON questions and shape files to generate SPARQL queries, ensuring only one LLM call per question."""

    # Load the JSON file with questions
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Read system prompt
    system_prompt = read_file(system_prompt_path)

    # Iterate over each question-answer pair in the JSON file
    for entry in data:
        question_id = entry.get("id")  # Use the original question ID
        question = entry.get("question_text", "").strip()
        entity_dict = entry.get("wikidata_entities_resolved", {})

        if not question or not entity_dict:
            print(f"⚠️ Skipping question ID {question_id} due to missing data.")
            continue

        # Collect all shape data for the entities in this question
        combined_shape_data = []
        entity_ids = list(entity_dict.values())  # Get all resolved entity Q-IDs

        for entity_id in entity_ids:
            shape_file_path = os.path.join(shape_dir, f"question_{question_id}_shape.shex")  # Match original dataset ID

            if not os.path.exists(shape_file_path):
                print(f"⚠️ WARNING: Shape file not found for question {question_id}, entity {entity_id}: {shape_file_path}")
                continue

            # Read shape data
            shape_data = read_file(shape_file_path)
            combined_shape_data.append(shape_data)

        if not combined_shape_data:
            print(f"⚠️ Skipping question ID {question_id} due to missing shape data.")
            continue

        # Merge all shape data for this question
        merged_shape_data = "\n\n".join(combined_shape_data)

        # Construct a single LLM prompt for the entire question
        full_prompt = construct_prompt(system_prompt, question, merged_shape_data)

        print(f"🔄 Generating SPARQL for question ID {question_id} with entities {entity_ids}...")

        # **Call the LLM only once for this question**
        response = call_llm(full_prompt, max_tokens, temperature, api_key, model, llm_switch)

        # Save the response once per question ID
        save_response(output_dir, question_id, response)

def main():
    parser = argparse.ArgumentParser(description="Generate SPARQL queries from an LLM for a dataset.")
    parser.add_argument("--json_path", required=True, help="Path to the JSON file containing extracted entities and questions.")
    parser.add_argument("--system_prompt_path", required=True, help="Path to the system prompt file.")
    parser.add_argument("--shape_path", required=True, help="Directory containing the ShEx shape files.")
    parser.add_argument("--output_dir", required=True, help="Directory to save the generated SPARQL responses.")
    parser.add_argument("--model", required=True, type=str, help="LLM model to use")
    parser.add_argument("--api_key", required=True, type=str, help="API key.")
    parser.add_argument("--max_tokens", default=512, type=int, help="Maximum number of tokens to generate.")
    parser.add_argument("--temperature", default=0.1, type=float, help="Sampling temperature.")
    parser.add_argument("--llm_switch", type=str, default="chatgpt", help="Define which llm to use.")

    args = parser.parse_args()

    process_json_and_shapes(
        json_path=args.json_path,
        shape_dir=args.shape_path,
        system_prompt_path=args.system_prompt_path,
        output_dir=args.output_dir,
        api_key=args.api_key,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature
        llm_switch=args.llm_switch
    )

if __name__ == "__main__":
    main()
