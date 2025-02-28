import argparse
import os
import requests
import json
import sys
from datetime import datetime
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

def call_local_llm(host, port, full_prompt, max_tokens, temperature):
    """Calls a local LLM server running on llama.cpp."""
    url = f"http://{host}:{port}/v1/completions"
    data = {
        "prompt": full_prompt,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=data)
        response.raise_for_status()
        result = response.json()
        return result.get("choices", [{}])[0].get("text", "No response text available.").strip()
    except requests.RequestException as e:
        sys.stderr.write(f"❌ ERROR: API call to local LLM failed: {e}\n")
        sys.exit(1)
    except json.JSONDecodeError:
        sys.stderr.write("❌ ERROR: Failed to decode API response\n")
        sys.exit(1)

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
        return completion.choices[0].message.content.strip()
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: API call to ChatGPT failed: {e}\n")
        sys.exit(1)

def save_response(output_dir, response):
    """Saves the response to a file."""
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "llm_response.txt")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"✅ Response saved to {output_file}")
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: Failed to write output file: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Call LLM API (local or remote) and save response.")
    parser.add_argument("--use_chatgpt", action="store_true", help="Use OpenAI ChatGPT API instead of local LLM.")
    parser.add_argument("--host", default="localhost", help="LLM server host (default: localhost)")
    parser.add_argument("--port", default=8000, type=int, help="LLM server port (default: 8000)")
    parser.add_argument("--model", required=False, type=str, help="OpenAI model to use (required for ChatGPT)")
    parser.add_argument("--openai_api_key", required=False, type=str, help="OpenAI API key (required for ChatGPT)")
    parser.add_argument("--user_prompt_path", required=True, help="Path to the user prompt file")
    parser.add_argument("--system_prompt_path", required=True, help="Path to the system prompt file")
    parser.add_argument("--shape_path", required=True, help="Path to the shape file (ShEx/SHACL)")
    parser.add_argument("--output_dir", required=True, help="Directory to save the response")
    parser.add_argument("--max_tokens", default=512, type=int, help="Maximum number of tokens to generate")
    parser.add_argument("--temperature", default=0.1, type=float, help="Sampling temperature")

    args = parser.parse_args()

    # Read all necessary inputs
    system_prompt = read_file(args.system_prompt_path)
    user_prompt = read_file(args.user_prompt_path)
    shape_data = read_file(args.shape_path)

    # Construct the final prompt ensuring SPARQL-only output
    full_prompt = construct_prompt(system_prompt, user_prompt, shape_data)

    # Call either local LLM or ChatGPT
    if args.use_chatgpt:
        response = call_chatgpt(full_prompt, args.max_tokens, args.temperature, args.openai_api_key, args.model)
    else:
        response = call_local_llm(args.host, args.port, full_prompt, args.max_tokens, args.temperature)

    # Save the response
    save_response(args.output_dir, response)
