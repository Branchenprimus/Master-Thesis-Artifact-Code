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
    def guess_rdf_format(path: str) -> str:
        """Heuristic to guess RDF serialization based on file extension."""
        if path.endswith(".ttl"):
            return "turtle"
        elif path.endswith(".rdf") or path.endswith(".xml"):
            return "xml"
        elif path.endswith(".nt"):
            return "nt"
        elif path.endswith(".jsonld"):
            return "json-ld"
        else:
            return "turtle"  # default

    @staticmethod
    def query_sparql_endpoint(sparql_query: str, endpoint_url: str) -> list:
        """Executes a SPARQL query against a remote endpoint and returns result values."""
        import requests
        headers = {"User-Agent": "SPARQLQueryBot/1.0"}
        data = {"query": sparql_query, "format": "json"}
        try:
            response = requests.get(endpoint_url, headers=headers, params=data)
            response.raise_for_status()
            json_response = response.json()
            return [
                binding[var]["value"]
                for var in json_response.get("head", {}).get("vars", [])
                for binding in json_response.get("results", {}).get("bindings", [])
                if var in binding and "value" in binding[var]
            ]
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def query_local_graph(sparql_query: str, graph_path: str) -> list:
        """Executes a SPARQL query against a local RDF graph and returns result values."""
        from rdflib import Graph
        try:
            g = Graph()
            g.parse(graph_path, format=Utils.guess_rdf_format(graph_path))
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