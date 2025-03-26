import json
import requests
from tqdm import tqdm
from time import sleep

# Load the JSON file
with open("/p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/QALD_Benchmark/QALD_9_plus/data/qald_9_plus_train_wikidata.json", "r") as f:
    data = json.load(f)

questions = data["questions"]
valid_questions = []
removed_log = []

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "QALD-Validator/1.0 (janwardenga@outlook.de)"
}

def extract_answer_set(results):
    bindings = results.get("bindings", [])
    extracted = set()
    for row in bindings:
        for var in row:
            val = row[var].get("value")
            if val:
                extracted.add(val)
    return extracted

# Iterate and validate each question
for q in tqdm(questions, desc="Validating SPARQL queries"):
    query_text = q.get("query", {}).get("sparql", "")
    golden_answers = q.get("answers", [])
    
    if not query_text or not golden_answers:
        removed_log.append({
            "id": q["id"],
            "question": q["question"][0]["string"],
            "reason": "Missing query or golden answer"
        })
        continue
    
    try:
        response = requests.get(
            WIKIDATA_ENDPOINT,
            params={"query": query_text},
            headers=HEADERS,
            timeout=35
        )
        response.raise_for_status()
        actual_results = response.json().get("results", {})
    except Exception as e:
        removed_log.append({
            "id": q["id"],
            "question": q["question"][0]["string"],
            "reason": f"Query failed: {str(e)}"
        })
        continue
    
    actual_set = extract_answer_set(actual_results)
    expected_set = extract_answer_set(golden_answers[0].get("results", {}))
    
    # If expected answers are not a subset of actual answers, log extended info
    if not expected_set.issubset(actual_set):
        removed_log.append({
            "id": q["id"],
            "question": q["question"][0]["string"],
            "reason": "Mismatch or outdated answer",
            "expected_set": list(expected_set),  # converting sets to lists for JSON compatibility
            "actual_set": list(actual_set)
        })
    else:
        valid_questions.append(q)
    
    sleep(1)  # Be gentle with the endpoint

# Create the cleaned dataset
cleaned_data = {"questions": valid_questions}

# Save cleaned dataset and log
cleaned_path = "/p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/util/extract_valid_from_QALD/results/cleaned_qald_9_plus_train_wikidata.json"
log_path = "/p/project1/hai_kg-rag-thesis/scripts/KG_Agent_MK2/util/extract_valid_from_QALD/results/removed_train_questions_log.json"

with open(cleaned_path, "w") as f:
    json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

with open(log_path, "w") as f:
    json.dump(removed_log, f, indent=2, ensure_ascii=False)

# Generate summary
summary = {
    "total_questions": len(questions),
    "valid_questions": len(valid_questions),
    "removed_questions": len(removed_log)
}

print(summary)
