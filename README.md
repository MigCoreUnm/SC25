# ARCS (Agentic RAG Code Synthesis)

ARCS is an agentic chain-of-thought system for retrieval-augmented code generation. It supports three evaluation pipelines:

- HumanEval (pass@1 on HumanEval benchmarks)
- TransCoder (translation accuracy)
- LANL CodeBLEU (CodeBLEU on a domain-specific LANL corpus, connectable to any vector-searchable database)

## Prerequisites

- Python 3.8 or 3.9  
- A virtual environment tool (venv or conda)  
- SambaNova API key 
- ChromaDB or another vector-store instance (for the LANL pipeline)

## Installation

```bash
# clone repository
git clone https://github.com/MigCoreUnm/SC25.git
cd SC25

# create and activate main environment
python3 -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# optional: create a secondary temporary environment
python3 -m venv temp_env_1
source temp_env1/bin/activate
pip install -r requirements.txt
