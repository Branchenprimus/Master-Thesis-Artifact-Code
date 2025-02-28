#!/usr/bin/py
import requests
import json
import argparse
import sys
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

# Argument parser for command-line arguments
parser = argparse.ArgumentParser(description="Send a request to the vLLM server and execute SPARQL query.")
parser.add_argument("--sparql_endpoint_url", type=str, required=True, help="SPARQL endpoint URL")
parser.add_argument("--model", type=str, required=True, help="Name of the model to use.")
parser.add_argument("--prompt_path", type=str, required=True, help="Path to the prompt text file.")
parser.add_argument("--host", type=str, default="127.0.0.1", help="vLLM server host (default: 127.0.0.1)")
parser.add_argument("--port", type=int, default=8000, help="vLLM server port (default: 8000)")
parser.add_argument("--api_key", type=str, default=None, help="API key for authentication (optional)")
parser.add_argument("--max_tokens", type=int, default=256, help="Max tokens for LLM inference (optional)")
parser.add_argument("--temperature", type=float, default=0.7, help="LLM temperature (optional)")
args = parser.parse_args()

# Construct API URL
API_URL = f"http://{args.host}:{args.port}/v1/chat/completions"  # Changed from /completions

# Read the prompt from the specified file
try:
    with open(args.prompt_path, "r", encoding="utf-8") as file:
        prompt_text = file.read().strip()
except Exception as e:
    print(f"Error reading the prompt file: {e}")
    sys.exit(1)

messages = [
    {"role": "system", "content": "You are a SPARQL expert"},
    {"role": "user", "content": prompt_text}
]

# Define the request payload
payload = {
    "model": args.model,
    "messages": messages,  # Use messages instead of prompt
    "temperature": args.temperature,
    "max_tokens": args.max_tokens,
    "stop": ["<｜end▁of▁thinking｜>"]  # Add stopping criteria
}

# Set headers
headers = {"Content-Type": "application/json"}
if args.api_key:
    headers["Authorization"] = f"Bearer {args.api_key}"

# Send the request
try:
    response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        response_data = response.json()
        generated_text = response_data["choices"][0]["text"].strip()

        # Ensure response contains a valid SPARQL query
        if "SELECT" in generated_text or "ASK" in generated_text or "CONSTRUCT" in generated_text:
            query = generated_text
            print("Generated SPARQL Query:\n", query)
        else:
            print("Error: LLM did not return a valid SPARQL query.")
            sys.exit(1)
    else:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"Failed to connect to LLM server: {e}")
    sys.exit(1)

# Initialize the SPARQLWrapper
sparql = SPARQLWrapper(args.sparql_endpoint_url)
sparql.setQuery(query)
sparql.setReturnFormat(JSON)

# Execute the query and process the results
try:
    results = sparql.query().convert()
    data = []
    for result in results["results"]["bindings"]:
        row = {key: value["value"] for key, value in result.items()}
        data.append(row)

    df = pd.DataFrame(data)
    print(df)
except Exception as e:
    print(f"Error executing SPARQL query: {e}")
