import argparse
import os
import requests
import json
import sys
from datetime import datetime

def call_llm_api(host, port, model_path, user_prompt_path, system_prompt_path, shape_path, output_dir, max_tokens, temperature):
    """ Calls the DeepSeek-V3 API and saves the response to a text file. """

    # Construct API URL
    url = f"http://{host}:{port}/v1/completions"

    # Read system prompt from file
    system_prompt = ""
    try:
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
    except Exception as e:
        sys.stderr.write(f"WARNING: Could not read system prompt file: {e}\n")

    # Read user prompt from file
    try:
        with open(user_prompt_path, "r", encoding="utf-8") as f:
            user_prompt = f.read().strip()
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: Could not read user prompt file: {e}\n")
        sys.exit(1)

    # Read shape data from file
    shape_data = ""
    try:
        with open(shape_path, "r", encoding="utf-8") as f:
            shape_data = f.read().strip()
    except Exception as e:
        sys.stderr.write(f"WARNING: Could not read shape file: {e}\n")

    # Combine system prompt, user prompt, and shape data
    full_prompt = f"{system_prompt}\n\nUser prompt:\n{user_prompt}\n\nShape:\n{shape_data}".strip()

    print(f"LOG: Full prompt prepared:\n{full_prompt}")

    # Request payload
    data = {
        "prompt": full_prompt,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    # Make API request
    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=data)
        response.raise_for_status()  # Raise error for bad response codes
        result = response.json()
        output_text = result.get("choices", [{}])[0].get("text", "No response text available.")
    except requests.RequestException as e:
        sys.stderr.write(f"❌ ERROR: API call failed: {e}\n")
        sys.exit(1)
    except json.JSONDecodeError:
        sys.stderr.write("❌ ERROR: Failed to decode API response\n")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save response to output file
    output_file = os.path.join(output_dir, "llm_response.txt")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"✅ Response saved to {output_file}")
    except Exception as e:
        sys.stderr.write(f"❌ ERROR: Failed to write output file: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Call LLM API and save response.")
    parser.add_argument("--host", required=True, help="LLM server host")
    parser.add_argument("--port", required=True, type=int, help="LLM server port")
    parser.add_argument("--model_path", required=True, help="Path to the model")
    parser.add_argument("--user_prompt_path", required=True, help="Path to the user prompt file")
    parser.add_argument("--system_prompt_path", required=True, help="Path to the system prompt file")
    parser.add_argument("--shape_path", required=True, help="Path to the shape file (ShEx/SHACL)")
    parser.add_argument("--output_dir", required=True, help="Directory to save the response")
    parser.add_argument("--max_tokens", required=True, type=int, help="Maximum number of tokens to generate")
    parser.add_argument("--temperature", required=True, type=float, help="Sampling temperature")

    args = parser.parse_args()

    call_llm_api(
        args.host,
        args.port,
        args.model_path,
        args.user_prompt_path,
        args.system_prompt_path,
        args.shape_path,
        args.output_dir,
        args.max_tokens,
        args.temperature,
    )
