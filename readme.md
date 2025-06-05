### **📌 README.md - KG Agent Pipeline**

## **🔹 Project Overview**
The **KG Agent** project is designed to extract structured knowledge from natural language queries (NLQs) and generate SPARQL queries to interact with **Wikidata**. The pipeline uses **large language models (LLMs)** to extract relevant entities, generate SPARQL queries, and verify their correctness.

---

## **🔹 Pipeline Overview**
The pipeline consists of multiple Python scripts, each responsible for a specific task in the **query generation and validation process**.

### **1️⃣ Extract Entities from NLQs (`extract_entity_list.py`)**
📌 **Goal:** Extract named entities from natural language questions.  
🔹 **Inputs:**  
- `--benchmark_dataset` → JSON file containing NLQs  
- `--api_key` → API key for LLM provider  
- `--num_questions` → Number of questions to process  
- `--model` → LLM model for entity extraction  
- `--llm_provider` → LLM API provider  

🔹 **Output:**  
- Extracted entities are stored in `extracted_nlq_sparql_with_entities.json`

---

### **2️⃣ Generate Shape Constraints (`generate_shape.py`)**
📌 **Goal:** Generate **ShEx shapes** (Shape Expressions) for the extracted entities to define constraints for SPARQL queries.  
🔹 **Inputs:**  
- `--shape_output_path` → Directory for saving shapes  
- `--target_json_file` → JSON file containing extracted entities  

🔹 **Output:**  
- Generated ShEx shapes in the specified output path.

---

### **3️⃣ Generate SPARQL Queries (`call_llm_api.py`)**
📌 **Goal:** Generate SPARQL queries using an LLM.  
🔹 **Inputs:**  
- `--model` → LLM model for SPARQL generation  
- `--api_key` → API key for LLM provider  
- `--json_path` → JSON file with extracted entities  
- `--system_prompt_path` → System prompt for the LLM  
- `--shape_path` → Path to ShEx shape constraints  
- `--output_dir` → Directory for storing LLM-generated SPARQL queries  

🔹 **Output:**  
- Generated SPARQL queries are saved in `llm_responses/`

---

### **4️⃣ Execute SPARQL Queries (`call_sparql_endpoint.py`)**
📌 **Goal:** Send both **baseline and LLM-generated** SPARQL queries to **Wikidata** and retrieve results.  
🔹 **Inputs:**  
- `--sparql_endpoint_url` → URL of the SPARQL endpoint  
- `--json_path` → JSON file containing generated SPARQL queries  

🔹 **Output:**  
- The results are appended to `extracted_nlq_sparql_with_entities.json`

---

### **5️⃣ Verify SPARQL Query Accuracy (`verify_sparql.py`)**
📌 **Goal:** Compare the LLM-generated SPARQL queries with the baseline to measure correctness.  
🔹 **Inputs:**  
- `--json_path` → JSON file with SPARQL query results  

🔹 **Output:**  
- **Metrics** (Precision, Recall, F1-score) are added to the JSON file.

---

### **6️⃣ Process and Summarize Results (`process_results.py`)**
📌 **Goal:** Aggregate results and generate a summary report.  
🔹 **Inputs:**  
- `--json_path` → JSON file with verification results  
- `--output_dir` → File to save the summary  

🔹 **Output:**  
- A text report (`processed.txt`) summarizing:
  - Total queries processed  
  - Correct/incorrect queries  
  - Invalid queries  
  - Precision, Recall, and F1-score  

---

## **🔹 1️⃣ Create & Activate a Virtual Environment**

### **On Linux/macOS:**
```sh
python3 -m venv KG_Agent_MK2_venv
source KG_Agent_MK2_venv/bin/activate
```

### **On Windows (PowerShell):**
```powershell
python -m venv KG_Agent_MK2_venv
KG_Agent_MK2_venv\Scripts\activate
```

---

## **🔹 2️⃣ Install Dependencies**
Once the virtual environment is activated, install the required Python packages:

```sh
pip install -r requirements.txt
```

---

## **🔹 3️⃣ Run the Pipeline**
Execute the **automated shell script** to run the full pipeline:

```sh
bash KG_Agent_MK2.sh
```

### **This script sequentially:**
✅ Extracts named entities from NLQs.  
✅ Generates shape constraints for SPARQL queries.  
✅ Generates SPARQL queries using an LLM.  
✅ Executes SPARQL queries on Wikidata.  
✅ Verifies query accuracy and correctness.  
✅ Processes and summarizes the results.  

---

## **🔹 5️⃣ View the Results**
Once execution completes, check the outputs:

### **Final processed results:**
```sh
test/output/processed.txt
```

### **SPARQL query validation results:**
```sh
test/output/extracted_nlq_sparql_with_entities.json
```

### **Log files for debugging:**
```sh
logs/
```

---

## **🔹 6️⃣ How to Reinstall or Update the Pipeline**
If you need to update the pipeline:

```sh
git pull origin main
pip install --upgrade -r requirements.txt
```

🚀 **Now your KG Agent Pipeline is ready to run!** 🎯
## **🔹 Results and Evaluation**
- The **final processed results** are saved in `processed.txt`.
- **SPARQL query correctness** is validated using **Precision, Recall, and F1-score**.
- Any **invalid queries or discrepancies** are flagged in the report.

🚀 **This pipeline automates knowledge graph querying using LLMs and validates results against baseline queries.** 🚀