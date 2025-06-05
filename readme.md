# SPARQL Query Generation Pipeline

A research pipeline that uses Large Language Models (LLMs) to automatically generate SPARQL queries from natural language questions, enhanced with shape-informed prompting for improved accuracy.

## Overview

The pipeline consists of multiple Python scripts, each responsible for a specific task in the **query generation and validation process**. The pipeline evaluates whether providing shape constraints (SHACL/ShEx) to LLMs improves their ability to generate accurate SPARQL queries from natural language questions. The system processes knowledge graph question-answering (KGQA) datasets and measures performance using standard evaluation metrics.

![Artifact Architecture](https://github.com/Branchenprimus/Master-Thesis-Tex/blob/main/images/artifact/architecture_diagram_small.drawio-1.png)
*System architecture showing the complete pipeline flow*
---

## Key Features

- **Automated Entity Extraction**: Identifies relevant entities from natural language questions
- **Dynamic Shape Generation**: Creates SHACL/ShEx constraints using the Shexer library
- **LLM-Powered Query Generation**: Generates SPARQL queries with shape-informed prompting
- **Result Verification**: Validates generated queries and computes accuracy metrics
- **Multi-dataset Support**: Works with Wikidata, DBpedia, and local knowledge graphs
- **Reproducible Experiments**: Structured logging and environment management

## System Requirements

### Minimum Requirements
- Ubuntu 22.04 or similar Linux distribution
- 2 vCPUs
- 4GB RAM
- 80GB storage

### Recommended (for large-scale experiments)
- High-performance computing environment
- Multi-core CPU (24+ cores recommended)
- 512GB+ RAM
- Rocky Linux 8 or similar

## Usage

### Basic Usage

Run the complete pipeline using the orchestrator script:

```bash
./KG_Agent_MK2.sh
```

The script automatically:
- Sources environment variables from `.env`
- Activates the Python virtual environment
- Creates indexed log directories with timestamps
- Executes all pipeline stages sequentially
- Generates comprehensive logs for each component
- Copies results to `Experiment_Results/` for analysis

### Environment Configuration

The pipeline reads configuration from a `.env` file with these key variables:

```bash
# LLM Configuration
LLM_PROVIDER_SPARQL_GENERATION=openai
LLM_PROVIDER_ENTITY_EXTRACTION=openai
MODEL_ENTITY_EXTRACTION=gpt-4o-mini
MODEL_SPARQL_GENERATION=gpt-4o-mini
API_KEY=your_api_key_here

# Dataset Configuration
BENCHMARK_DATASET=path/to/dataset.json
NUM_QUESTIONS=50  # 0 for all questions
DATASET_TYPE=wikidata
IS_LOCAL_GRAPH=false

# SPARQL Endpoint
SPARQL_ENDPOINT_URL=https://query.wikidata.org/sparql

# Shape Configuration
SHAPE_TYPE=shex
ANNOTATION=true
BASELINE_RUN=false

# Retry Configuration
MAX_CONSECUTIVE_RETRIES=3
```

### Output Structure

Each run creates a timestamped directory structure:

```
logs/DD-MM-YYYY/KG_Agent_MK2_X/
├── 1_extract_entity_list.out/.err
├── 2_generate_shape.out/.err
├── 3_call_llm_api.out/.err
├── 4_verify_sparql.out/.err
├── 5_track_files.log/.err
├── 6_job.out/.err
├── 7_convert_summaries_to_csv.out/.err
├── misc/
│   ├── meta/         # File tracking metadata
│   └── temp/         # Intermediate JSON files and shapes
└── Experiment_Results/  # Final results (copied when NUM_QUESTIONS=50)
```

### Pipeline Components

The pipeline consists of four sequential stages orchestrated by `KG_Agent_MK2.sh`:

#### 1. Entity Extraction (`extract_entity_list.py`)
![Entity Extraction Flow](https://github.com/Branchenprimus/Master-Thesis-Tex/blob/main/images/artifact/extract_entity_list.drawio-1.png)

Extracts relevant entities from natural language questions using LLM prompting.

**Key Parameters:**
- `--benchmark_dataset`: Input JSON file with natural language questions
- `--model`: LLM model for entity extraction (e.g., deepseek-chat, gpt-4o-mini)
- `--api_key`: API key for LLM provider
- `--num_questions`: Number of questions to process (0 = all)
- `--baseline_run`: Skip entity extraction for baseline comparison

#### 2. Shape Generation (`generate_shape.py`)
![Shape Generation Flow](https://github.com/Branchenprimus/Master-Thesis-Tex/blob/main/images/artifact/generate_shape.drawio-1.png)

Generates SHACL or ShEx shape constraints for extracted entities using the Shexer library.

**Key Parameters:**
- `--shape_output_path`: Directory for saving generated shapes
- `--target_json_file`: JSON file containing extracted entities
- `--shape_type`: SHACL or ShEx format
- `--existing_shape_path`: Use pre-existing shapes (optional)
- `--annotation`: Include shape annotations

#### 3. SPARQL Query Generation (`call_llm_api.py`)
![Query Generation Flow](https://github.com/Branchenprimus/Master-Thesis-Tex/blob/main/images/artifact/call_llm_api.drawio-1.png)

Creates SPARQL queries using shape-informed prompting with retry mechanisms for validation.

**Key Parameters:**
- `--json_path`: Input file with entities and shapes
- `--system_prompt_path`: System prompt template for query generation
- `--shape_path`: Directory containing shape constraints
- `--max_retries`: Maximum retry attempts for failed queries
- `--sparql_endpoint_url`: SPARQL endpoint for query validation

#### 4. Result Verification (`verify_sparql.py`)
![Result Verification Flow](https://github.com/Branchenprimus/Master-Thesis-Tex/blob/main/images/artifact/verify_sparql.drawio-1.png)

Validates generated queries against gold standard answers and computes evaluation metrics.

**Key Parameters:**
- `--json_path`: File containing generated SPARQL queries
- `--log_dir`: Directory for experiment logs and results
- `--run_index`: Unique identifier for this experimental run

**Output:** CSV file with F1-score, precision, recall, and execution metrics

## Input Data Format

The pipeline expects input data in QALD-compatible JSON format:

```json
{
  "questions": [
    {
      "id": "1",
      "question": [
        {
          "language": "en",
          "string": "What is the capital of France?"
        }
      ],
      "query": {
        "sparql": "SELECT ?capital WHERE { wd:Q142 wdt:P36 ?capital }"
      },
      "answers": [
        {
          "head": {"vars": ["capital"]},
          "results": {
            "bindings": [
              {"capital": {"type": "uri", "value": "http://www.wikidata.org/entity/Q90"}}
            ]
          }
        }
      ]
    }
  ]
}
```

## Output

The pipeline generates several output files:

- **entities.json**: Extracted entities with their identifiers
- **shapes/**: Directory containing generated shape constraints
- **queries.json**: Generated SPARQL queries with metadata
- **results.csv**: Final evaluation metrics and performance data