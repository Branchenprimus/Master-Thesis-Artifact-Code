import os
import logging
import requests
from rdflib import Graph

class Utils:
    @staticmethod
    def str_to_bool(value: str) -> bool:
        """Convert a string to a boolean."""
        return value.lower() in ('true', '1', 'yes')

    @staticmethod
    def is_json_file(filename: str) -> bool:
        """Check if the file has a .json extension."""
        return filename.lower().endswith('.json')

    @staticmethod
    def ensure_list(value):
        """Wrap value in a list if it's not already a list."""
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def safe_get(d: dict, key, default=None):
        """Safely get a value from a dictionary."""
        return d.get(key, default)

    @staticmethod
    def read_file(file_path: str) -> str:
        """Reads content from a file and returns it as a string."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"WARNING: Could not read file {file_path}: {e}")
            return ""

    @staticmethod
    def query_sparql_endpoint(sparql_query: str, endpoint_url: str) -> list:
        """
        Executes a SPARQL query against a remote endpoint and returns the result values.

        Args:
            sparql_query: The SPARQL query string.
            endpoint_url: The URL of the SPARQL endpoint.

        Returns:
            A list of result values (as strings), or a dictionary with {"error": "..."}.
        """
        headers = {
            "User-Agent": "SPARQLQueryBot/1.0 (contact: example@example.com)"
        }
        data = {
            "query": sparql_query,
            "format": "json"
        }

        try:
            response = requests.get(endpoint_url, headers=headers, params=data)
            response.raise_for_status()
            json_response = response.json()

            vars_ = json_response.get("head", {}).get("vars", [])
            bindings = json_response.get("results", {}).get("bindings", [])

            return [
                binding[var]["value"]
                for var in vars_
                for binding in bindings
                if var in binding and "value" in binding[var]
            ]

        except requests.exceptions.RequestException as e:
            return {"error": str(e)} 

    @staticmethod
    def guess_rdf_format(file_path: str) -> str:
        """Guesses RDF serialization format based on file extension."""
        if file_path.endswith(".ttl"):
            return "turtle"
        elif file_path.endswith(".nt"):
            return "nt"
        elif file_path.endswith(".rdf") or file_path.endswith(".xml"):
            return "xml"
        else:
            return "turtle"  # default fallback

    @staticmethod
    def query_local_graph(sparql_query: str, graph_folder: str) -> list:
        """
        Executes a SPARQL query against a local RDF graph composed from multiple RDF files in a folder.
        
        Args:
            sparql_query: SPARQL query string.
            graph_folder: Path to a folder containing RDF files (.ttl, .rdf, .nt).

        Returns:
            List of stringified query result values or {"error": "..."} on failure.
        """
        try:
            g = Graph()

            for fname in os.listdir(graph_folder):
                if fname.endswith((".ttl", ".rdf", ".nt")):
                    fpath = os.path.join(graph_folder, fname)
                    fmt = Utils.guess_rdf_format(fpath)
                    g.parse(fpath, format=fmt)

            if len(g) == 0:
                return {"error": "No RDF triples were loaded from the folder."}

            qres = g.query(sparql_query)
            return [str(val) for row in qres for val in row]

        except Exception as e:
            return {"error": str(e)}
        
    @staticmethod
    def is_faulty_result(result):
        if isinstance(result, dict) and "error" in result:
            return True
        if not result:
            return True
        if all(str(r).strip() == "0" for r in result):
            return True
        return False