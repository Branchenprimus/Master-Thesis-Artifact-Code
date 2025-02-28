#!/usr/bin/env python3
import requests
import json
import argparse
import sys
import os
import re
import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON

def read_llm_response(file_path):
    """Reads and extracts the SPARQL query from the LLM-generated response file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            query = file.read().strip()
        
        # Remove any markdown code block formatting
        query = re.sub(r"^```sparql|```$", "", query, flags=re.MULTILINE).strip()

        # Ensure it's a valid SPARQL query
        if not any(keyword in query.upper() for keyword in ["SELECT", "ASK", "CONSTRUCT", "DESCRIBE"]):
            print(f"ERROR: The extracted text is not a valid SPARQL query:\n{query}")
            sys.exit(1)
        
        print("SPARQL query successfully extracted and validated.")
        return query

    except Exception as e:
        print(f"ERROR: Could not read the LLM response file: {e}")
        sys.exit(1)

def execute_sparql_query(endpoint_url, query):
    """Sends the SPARQL query to the endpoint and returns the results."""
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        print(f"🔍 Executing query against: {endpoint_url}")
        results = sparql.query().convert()

        # Convert results to DataFrame
        data = []
        for result in results["results"]["bindings"]:
            row = {key: value["value"] for key, value in result.items()}
            data.append(row)

        df = pd.DataFrame(data)
        return df

    except Exception as e:
        print(f"ERROR: Failed to execute SPARQL query: {e}")
        sys.exit(1)

def save_results(df, output_path):
    """Saves the query results to a CSV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        df.to_csv(output_path, index=False)
        print(f"SPARQL results saved to: {output_path}")
    except Exception as e:
        print(f"ERROR: Could not save SPARQL results: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify and execute SPARQL query from LLM output.")
    parser.add_argument("--sparql_endpoint_url", type=str, required=True, help="SPARQL endpoint URL")
    parser.add_argument("--response_file", type=str, required=True, help="Path to the LLM-generated SPARQL query file")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the SPARQL response CSV")
    args = parser.parse_args()

    # Read and verify SPARQL query
    query = read_llm_response(args.response_file)

    # Execute the SPARQL query
    df = execute_sparql_query(args.sparql_endpoint_url, query)

    # Save results
    output_file = os.path.join(args.output_dir, "SPARQL_response.csv")
    save_results(df, output_file)
