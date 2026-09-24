# TigerGraph Agentic Fraud Investigation & Next-Best Action (HHGOA)

An autonomous AI Agent system powered by TigerGraph, GraphRAG, and reasoning under uncertainty to investigate fraud, progress cases, coordinate policy-approved evidence gathering, and recommend next-best actions.

## Key Features

- **TigerGraph Graph Modeling & GSQL Traversal**: Detect complex multi-hop fraud patterns (device rings, synthetic identity bursts, impossible travel, merchant collusion).
- **TigerGraph MCP Server Integration**: Exposes graph queries and neighborhood subgraphs directly to agent tool calls.
- **GraphRAG & Policy Grounding**: Merges deep graph context with bank fraud policies, typologies, and regulatory criteria.
- **Uncertainty-Aware Next-Best Action (NBA)**:
  - Formulates pre-evidence action and required approval route.
  - Gathers targeted evidence via interactive mock services (SMS verification, step-up auth, analyst review).
  - Updates post-evidence action and approval route.
- **Automated Case Memory & Persistence**: Queries historical cases (4 months of closed investigations) and persists new case findings back into the TigerGraph knowledge graph.
- **Regulatory Reporting**: Auto-generates FinCEN-compliant Suspicious Activity Reports (SAR).
- **Benchmark Suite**: Pre-configured harness to run against the 20 benchmark test cases.

## Project Structure

```
├── docs/                 # Hackathon brief and documentation
├── schema/               # TigerGraph GSQL graph schema definition
├── gsql/queries/         # GSQL queries for pattern detection & subgraphs
├── src/
│   ├── agent/            # Agent state machine, domain models, investigator
│   ├── tigergraph/       # TigerGraph connector, query runner, and MCP wrapper
│   ├── actions/          # Interactive mock services (SMS, Step-Up, Freeze)
│   ├── rag/              # Policy engine, fraud typologies, GraphRAG logic
│   └── evaluation/       # Benchmark runner and answer file generator
├── tests/                # Automated pytest suite
└── requirements.txt
```

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure credentials in `.env`:
   ```bash
   cp .env.example .env
   ```
3. Run test suite:
   ```bash
   pytest -v tests/
   ```
4. Run sample case investigation:
   ```bash
   python -m src.evaluation.runner --case-id case_01 --verbose
   ```
