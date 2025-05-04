import json
import os
import argparse
import time
from tqdm import tqdm
from rdflib import Graph

# ========== Argument Parsing ==========
parser = argparse.ArgumentParser(description="Validate KGQA dataset using local RDF graph with rdflib.")
parser.add_argument("benchmark_dataset", help="QALD-style dataset file (JSON)")
parser.add_argument("output_dir", help="Directory to save cleaned dataset and logs")
parser.add_argument("rdf_file", help="Path to the RDF knowledge graph file")
parser.add_argument("--rdf_format", default="xml", help="RDF format (e.g., xml, ttl, nt, json-ld). Default: xml")
args = parser.parse_args()

# ========== Load RDF ==========
print(f"🔄 Loading RDF graph from {args.rdf_file} ...")
graph = Graph()
graph.parse(args.rdf_file, format=args.rdf_format)
print(f"✅ RDF graph loaded with {len(graph)} triples.\n")

# ========== Load KGQA Dataset ==========
with open(args.benchmark_dataset, "r") as f:
    data = json.load(f)

questions = data["questions"]
valid_questions = []
removed_log = []

# ========== Helpers ==========
def extract_answer_set(results):
    if isinstance(results, bool):
        raise TypeError("Cannot extract bindings from a boolean result (ASK query).")
    extracted = set()
    for row in results:
        for val in row:
            if val is not None:
                extracted.add(str(val))
    return extracted

def extract_expected_set(results_obj):
    bindings = results_obj.get("bindings", [])
    extracted = set()
    for row in bindings:
        for var in row:
            val_obj = row[var]
            if isinstance(val_obj, dict):
                val = val_obj.get("value")
                if val:
                    extracted.add(val)
            else:
                print(f"  ⚠️ Unexpected value format in expected set: {val_obj} (type: {type(val_obj)})")
    return extracted

# ========== Main Loop ==========
for idx, q in enumerate(tqdm(questions, desc="Validating queries locally")):
    q_id = q.get("id", f"index_{idx}")
    question_text = q["question"][0]["string"]
    query_text = q.get("query", {}).get("sparql", "")
    golden_answers = q.get("answers", [])

    print(f"\n→ Processing ID {q_id}: {question_text[:60]}...")

    if not query_text or not golden_answers:
        print("  ⚠️ Skipped: missing query or answers.")
        removed_log.append({
            "id": q_id,
            "question": question_text,
            "reason": "Missing query or golden answer"
        })
        continue

    expected_answer = golden_answers[0]

    try:
        start = time.time()
        result = graph.query(query_text)
        elapsed = time.time() - start
        print(f"  ✅ Query executed in {elapsed:.2f}s.")
    except Exception as e:
        print(f"  ❌ Query failed: {str(e)}")
        removed_log.append({
            "id": q_id,
            "question": question_text,
            "reason": f"Query failed: {str(e)}",
            "query": query_text
        })
        continue

# ====== Handle ASK Queries ======
if "boolean" in expected_answer:
    expected_bool = expected_answer["boolean"]
    actual_bool = None

    try:
        # First try .askAnswer (real ASK queries)
        actual_bool = getattr(result, "askAnswer", None)

        # If that didn't work, it's likely a SELECT returning a boolean in ?res
        if actual_bool is None:
            bindings = list(result.bindings)
            if bindings:
                res_val = bindings[0].get(None) or bindings[0].get("res")
                if res_val:
                    str_val = str(res_val).strip().lower()
                    if str_val == "true":
                        actual_bool = True
                    elif str_val == "false":
                        actual_bool = False

        if actual_bool == expected_bool:
            print("  ✅ ASK-style result matched.")
            valid_questions.append(q)
        else:
            print(f"  ❌ ASK-style mismatch. Got: {actual_bool}, Expected: {expected_bool}")
            removed_log.append({
                "id": q_id,
                "question": question_text,
                "reason": "ASK result mismatch",
                "expected_bool": expected_bool,
                "actual_bool": actual_bool,
                "query": query_text
            })

    except Exception as e:
        print(f"  ❌ Failed to evaluate ASK-like query: {str(e)}")
        removed_log.append({
            "id": q_id,
            "question": question_text,
            "reason": "ASK result error",
            "error": str(e),
            "query": query_text
        })

    sleep(args.sleep)
    continue  # Skip SELECT handling


    # ====== Handle SELECT Queries ======
    elif "results" in expected_answer:
        try:
            actual_set = extract_answer_set(result)
            expected_set = extract_expected_set(expected_answer.get("results", {}))

            if expected_set.issubset(actual_set):
                print("  ✅ SELECT result matched.")
                valid_questions.append(q)
            else:
                print("  ⚠️ SELECT mismatch.")
                removed_log.append({
                    "id": q_id,
                    "question": question_text,
                    "reason": "Mismatch or outdated answer",
                    "expected_set": list(expected_set),
                    "actual_set": list(actual_set),
                    "query": query_text
                })

        except Exception as e:
            print(f"  ❌ SELECT comparison failed: {str(e)}")
            removed_log.append({
                "id": q_id,
                "question": question_text,
                "reason": f"SELECT result error: {str(e)}",
                "query": query_text
            })

    # ====== Unknown Answer Type ======
    else:
        print("  ❓ Unknown answer format.")
        removed_log.append({
            "id": q_id,
            "question": question_text,
            "reason": "Unknown answer format",
            "answer_raw": expected_answer,
            "query": query_text
        })


# ========== Output ==========
os.makedirs(args.output_dir, exist_ok=True)
base_name = os.path.splitext(os.path.basename(args.benchmark_dataset))[0]
cleaned_path = os.path.join(args.output_dir, f"{base_name}_cleaned.json")
log_path = os.path.join(args.output_dir, f"{base_name}_removed_log.json")

with open(cleaned_path, "w") as f:
    json.dump({"questions": valid_questions}, f, indent=2, ensure_ascii=False)

with open(log_path, "w") as f:
    json.dump(removed_log, f, indent=2, ensure_ascii=False)

# ========== Summary ==========
summary = {
    "total_questions": len(questions),
    "valid_questions": len(valid_questions),
    "removed_questions": len(removed_log)
}
print("\n📝 Validation complete.")
print(json.dumps(summary, indent=2))
