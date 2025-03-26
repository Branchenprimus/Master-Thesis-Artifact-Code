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

def call_chatgpt(full_prompt, max_tokens, temperature, openai_api_key, model):
    """Calls OpenAI's GPT model via the ChatGPT API."""
    client = OpenAI(api_key=openai_api_key)
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
        print(f"ChatGPT completion object: {completion}")
        return completion.choices[0].message.content.strip()
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: API call to ChatGPT failed: {e}\n")
        sys.exit(1)

def save_response(output_dir, pair_id, entity_id, response):
    """Saves the response to a file, removing SPARQL code block formatting."""
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"pair_{pair_id}_entity_{entity_id}.sparql")

    # Remove code block formatting
    response = response.replace("```sparql", "").replace("```", "").strip()

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"✅ Response saved to {output_file}")
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: Failed to write output file: {e}\n")
        sys.exit(1)


def process_json_and_shapes(json_path, shape_dir, system_prompt_path, output_dir, openai_api_key, model, max_tokens, temperature):
    """Iterates over the JSON questions and corresponding shape files to generate SPARQL queries."""
    # Load the JSON file with questions
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Read system prompt
    system_prompt = read_file(system_prompt_path)

    # Iterate over each question-answer pair in the JSON file
    for idx, entry in enumerate(data):
        question = entry.get("question", "").strip()
        entity_ids = entry.get("entities_extracted", "").split(", ")

        if not question or not entity_ids:
            print(f"Skipping pair {idx} due to missing data.")
            continue

        for entity_id in entity_ids:
            shape_file_path = os.path.join(shape_dir, f"pair_{idx}_shape.shex")

            if not os.path.exists(shape_file_path):
                print(f"⚠️ WARNING: Shape file not found for pair {idx}, entity {entity_id}: {shape_file_path}")
                continue

            shape_data = read_file(shape_file_path)
            full_prompt = construct_prompt(system_prompt, question, shape_data)
            
            

            print(f"🔄 Generating SPARQL for pair {idx}, entity {entity_id}...")

            response = call_chatgpt(full_prompt, max_tokens, temperature, openai_api_key, model)
            save_response(output_dir, idx, entity_id, response)

def main():
    parser = argparse.ArgumentParser(description="Generate SPARQL queries from an LLM for a dataset.")
    parser.add_argument("--json_path", required=True, help="Path to the JSON file containing extracted entities and questions.")
    parser.add_argument("--system_prompt_path", required=True, help="Path to the system prompt file.")
    parser.add_argument("--shape_path", required=True, help="Directory containing the ShEx shape files.")
    parser.add_argument("--output_dir", required=True, help="Directory to save the generated SPARQL responses.")
    parser.add_argument("--model", required=True, type=str, help="OpenAI model to use (e.g., gpt-4-turbo).")
    parser.add_argument("--openai_api_key", required=True, type=str, help="OpenAI API key.")
    parser.add_argument("--max_tokens", default=512, type=int, help="Maximum number of tokens to generate.")
    parser.add_argument("--temperature", default=0.1, type=float, help="Sampling temperature.")

    args = parser.parse_args()

    process_json_and_shapes(
        json_path=args.json_path,
        shape_dir=args.shape_path,
        system_prompt_path=args.system_prompt_path,
        output_dir=args.output_dir,
        openai_api_key=args.openai_api_key,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature
    )

if __name__ == "__main__":
    main()
