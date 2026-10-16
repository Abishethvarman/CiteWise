# Contributing to CiteWise

Thanks for helping improve a local, evidence-first research tool.

## Ground rules

- Do not add confidential documents, client files, API keys, or model weights.
- Do not present a string match as legal correctness.
- Keep document text out of ordinary logs.
- Do not add a commercial inference provider that runs by default. Optional providers must stay disabled unless a user turns them on, and this release does not include one.
- Prefer a failing test before changing retrieval, verification, or prompt fencing.

## Setup

Use Python 3.12 and Node.js 22.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ../frontend
npm install
```

On Windows, activate the virtual environment with `.venv\Scripts\activate`.

## Checks

```bash
cd backend
ruff check .
pytest
cd ..
python scripts/evaluate_retrieval.py
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

The default tests do not download a language model. Set `CITEWISE_RUN_OLLAMA=1` to run the optional Ollama test in `backend/tests/test_ollama_integration.py`.

## Pull requests

Describe the behaviour you changed and how you tested it. Do not paste benchmark numbers you did not produce by running the evaluation script.
