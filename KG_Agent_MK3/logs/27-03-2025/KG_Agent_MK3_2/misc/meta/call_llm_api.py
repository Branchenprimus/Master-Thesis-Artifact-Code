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
    """Constructs a structured prompt for a single question."""
    return f"""{system_prompt}

### User Query:
{user_prompt}

### Shape Constraints:
{shape_data}

### Expected SPARQL Query:
```sparql
"""

def call_llm(full_prompt, max_tokens, temperature, api_key, model, llm_provider):
    """Calls the LLM API for a single question."""
    try:
        if llm_provider == "openai":
            client = OpenAI(api_key=api_key)
        elif llm_provider == "deepseek":
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
            
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
        sys.stderr.write(f"❌ ERROR: API call failed: {e}\n")
        sys.exit(1)

def save_response(json_path, question_id, response):
    """Updates a single question entry in the JSON file."""
    response = response.replace("```sparql", "").replace("```", "").strip()
    
    try:
        with open(json_path, "r+", encoding="utf-8") as file:
            data = json.load(file)
            for entry in data:
                if str(entry.get("id")) == str(question_id):
                    entry["llm_generated_sparql"] = response
                    file.seek(0)
                    json.dump(data, file, indent=4, ensure_ascii=False)
                    file.truncate()
                    print(f"✅ Response saved for question ID {question_id}")
                    return
            raise ValueError(f"Question ID {question_id} not found")
    except Exception as e:
        sys.stderr.write(f"❌ Error saving response: {e}\n")
        sys.exit(1)

def process_single_question(args, question_index):
    """Processes one question specified by index."""
    # Load the JSON data
    try:
        with open(args.json_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if question_index < 0 or question_index >= len(data):
                raise ValueError(f"Invalid question index {question_index}")
            entry = data[question_index]
    except Exception as e:
        sys.stderr.write(f"❌ Error loading data: {e}\n")
        sys.exit(1)

    # Load system prompt
    system_prompt = read_file(args.system_prompt_path)
    if not system_prompt:
        sys.stderr.write("❌ Error: System prompt is empty\n")
        sys.exit(1)

    # Handle shape data
    if args.is_local_graph:
        shape_path = os.path.join(args.shape_path, "local_graph_shape.shex")
    else:
        shape_path = os.path.join(args.shape_path, f"question_{entry['id']}_shape.shex")
    
    shape_data = read_file(shape_path)
    if not shape_data:
        sys.stderr.write(f"❌ Error: No shape data found at {shape_path}\n")
        sys.exit(1)

    # Construct and execute prompt
    full_prompt = construct_prompt(
        system_prompt,
        entry["question_text"],
        shape_data
    )
    
    response = call_llm(
        full_prompt,
        args.max_tokens,
        args.temperature,
        args.api_key,
        args.model,
        args.llm_provider
    )

    # Save the result
    save_response(args.json_path, entry["id"], response)

def main():
    parser = argparse.ArgumentParser(description="Generate SPARQL query for a single question")
    parser.add_argument("--json_path", required=True, help="Path to input JSON file")
    parser.add_argument("--system_prompt_path", required=True, help="Path to system prompt file")
    parser.add_argument("--shape_path", required=True, help="Directory containing shape files")
    parser.add_argument("--model", required=True, help="LLM model to use")
    parser.add_argument("--api_key", required=True, help="API key")
    parser.add_argument("--max_tokens", type=int, default=512, help="Max tokens for response")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--llm_provider", default="openai", help="LLM provider (openai/deepseek)")
    parser.add_argument("--is_local_graph", type=bool, required=True, help="Use local graph")
    parser.add_argument("--question_index", type=int, required=True, help="Question index to process")

    args = parser.parse_args()
    process_single_question(args, args.question_index)

if __name__ == "__main__":
    main()