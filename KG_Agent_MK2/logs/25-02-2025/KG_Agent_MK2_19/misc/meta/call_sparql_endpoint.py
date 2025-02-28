#!/usr/bin/env python3
import requests
import json
import argparse
import sys
import os
import re
import pandas as pd
import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON

def read_sparql_query(file_path):
    """Reads and extracts the SPARQL query from an LLM-generated SPARQL file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            query = file.read().strip()

        # Ensure it's a valid SPARQL query
        if not any(keyword in query.upper() for keyword in ["SELECT", "ASK", "CONSTRUCT", "DESCRIBE"]):
            print(f"❌ ERROR: Invalid SPARQL query in {file_path}:\n{query}")
            return None

        print(f"✅ Successfully extracted SPARQL query from {file_path}")
        return query

    except Exception as e:
        print(f"❌ ERROR: Could not read file {file_path}: {e}")
        return None

def execute_sparql_query(endpoint_url, ttl_file, query):
    """Executes the SPARQL query on a remote endpoint or a local RDF file."""
    if endpoint_url.lower() == "local":
        return execute_local_sparql(ttl_file, query)
    else:
        return execute_remote_sparql(endpoint_url, query)

def execute_remote_sparql(endpoint_url, query):
    """Executes a SPARQL query against a remote SPARQL endpoint."""
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        print(f"🔍 Executing query against remote endpoint: {endpoint_url}")
        results = sparql.query().convert()

        # Convert results to a list of dictionaries
        data = []
        for result in results["results"]["bindings"]:
            row = {key: value["value"] for key, value in result.items()}
            data.append(row)

        return data

    except Exception as e:
        print(f"❌ ERROR: Failed to execute SPARQL query on remote endpoint: {e}")
        return None

def execute_local_sparql(ttl_file, query):
    """Executes a SPARQL query against a local RDF dataset."""
    g = rdflib.Graph()

    try:
        print(f"📂 Loading local RDF graph from: {ttl_file}")
        g.parse(ttl_file, format="turtle")

        print(f"🔍 Executing query on local RDF graph")
        qres = g.query(query)

        # Convert results to a list of dictionaries
        data = []
        for row in qres:
            data.append({f"var_{i}": str(value) for i, value in enumerate(row)})

        return data

    except Exception as e:
        print(f"❌ ERROR: Failed to execute SPARQL query on local RDF graph: {e}")
        return None

def process_sparql_files(sparql_folder, endpoint_url, ttl_file, json_output):
    """Iterates over SPARQL files, executes queries, and updates the JSON output."""
    # Load existing JSON file
    if os.path.exists(json_output):
        with open(json_output, "r", encoding="utf-8") as file:
            json_data = json.load(file)
    else:
        print(f"❌ ERROR: JSON output file not found: {json_output}")
        sys.exit(1)

    # Ensure JSON data is a list
    if not isinstance(json_data, list):
        print("❌ ERROR: JSON output file format is incorrect. Expected a list.")
        sys.exit(1)

    # Iterate through JSON entries and match with SPARQL files
    for entry in json_data:
        sparql_file = os.path.join(sparql_folder, f"pair_{entry['id']}.sparql")
        print(f"sparql_file: {sparql_file}")

        if os.path.exists(sparql_file):
            query = read_sparql_query(sparql_file)

            if query:
                results = execute_sparql_query(endpoint_url, ttl_file, query)
                entry["llm_derived_SPARQL_response"] = results
                print(f"✅ Added SPARQL results for question ID {entry['id']}")
            else:
                print(f"⚠️ Skipping question ID {entry['id']} due to invalid query.")
        else:
            print(f"⚠️ No SPARQL file found for question ID {entry['id']}, skipping.")

    # Save updated JSON file
    with open(json_output, "w", encoding="utf-8") as file:
        json.dump(json_data, file, indent=4, ensure_ascii=False)

    print(f"✅ Updated JSON file saved to: {json_output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute SPARQL queries from LLM-generated files and update JSON output.")
    parser.add_argument("--sparql_folder", type=str, required=True, help="Path to folder containing LLM-generated SPARQL queries")
    parser.add_argument("--sparql_endpoint_url", type=str, required=True, help="SPARQL endpoint URL or 'local' for local execution")
    parser.add_argument("--ttl_file", type=str, required=False, help="Path to the local Turtle RDF file (Required if using local execution)")
    parser.add_argument("--json_output", type=str, required=True, help="Path to the JSON output file")

    args = parser.parse_args()

    print(f"sparql_folder: {args.sparql_folder}")
    print(f"sparql_endpoint_url: {args.sparql_endpoint_url}")
    print(f"ttl_file: {args.ttl_file}")
    print(f"json_output: {args.json_output}")

    process_sparql_files(args.sparql_folder, args.sparql_endpoint_url, args.ttl_file, args.json_output)
