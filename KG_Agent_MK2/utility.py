import os
import requests
from rdflib import Graph
from typing import Union
import time

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
    def query_sparql_endpoint(sparql_query: str, endpoint_url: str, max_retries: int = 15, backoff_factor: float = 1.5) -> Union[list, dict]:
        """
        Executes a SPARQL query against a remote endpoint and returns the result values.
        Implements retry logic in case of 502/503/504 errors.

        Args:
            sparql_query: The SPARQL query string.
            endpoint_url: The URL of the SPARQL endpoint.
            max_retries: Maximum number of retry attempts.
            backoff_factor: Exponential backoff factor in seconds.

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

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(endpoint_url, headers=headers, params=data, timeout=20)
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

            except requests.exceptions.HTTPError as http_err:
                # Retry on transient errors
                if response.status_code in [502, 503, 504]:
                    if attempt < max_retries:
                        sleep_time = backoff_factor ** attempt
                        print(f"[Retry {attempt}/{max_retries}] HTTP {response.status_code}: Retrying in {sleep_time:.1f}s...")
                        time.sleep(sleep_time)
                        continue
                    elif response.status_code == 400:
                        return {
                            "error": "Bad Request (400)",
                            "message": str(http_err),
                            "query": sparql_query,
                            "endpoint": endpoint_url
                        }                    
                else:
                    return {"error": f"HTTPError: {http_err}"}

            except requests.exceptions.RequestException as e:
                # Handle other types of network-related errors
                return {"error": f"RequestException: {e}"}

        return {"error": "Failed to retrieve response after multiple attempts."}

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
        # Case 1: SPARQL or API error structure
        if isinstance(result, dict) and "error" in result:
            return True

        # Case 2: Result is None, empty list, or empty dict
        if result is None or (isinstance(result, (list, dict)) and not result):
            return False

        # Case 3: All-zero or meaningless values
        if isinstance(result, list) and all(str(r).strip() in {"0", "0.0", "", "null", "None"} for r in result):
            return False

        # Everything else is assumed valid
        return False

    
    @staticmethod
    def resolve_llm_provider(llm_provider: str) -> str:
        """Resolves the LLM provider to a specific string."""
        if llm_provider == "openai":
            return None
        elif llm_provider == "deepseek":
            return "https://api.deepseek.com/v1"
        elif llm_provider == "alibaba":
            return "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        elif llm_provider == "anthropic":
            return "https://api.anthropic.com/v1/"
        elif llm_provider == "groq":
            return "https://api.groq.com/openai/v1"
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")