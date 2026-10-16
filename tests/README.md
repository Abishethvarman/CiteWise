# Tests

Automated tests live in `backend/tests` and `frontend/src/test`.

`tests/eval_corpus.json` is a small synthetic retrieval set. It is a development fixture, not a legal benchmark. Run it with:

```bash
python scripts/evaluate_retrieval.py
```

`tests/fixtures/prompt_injection.txt` is hostile text used to confirm that document contents stay inside the evidence fence and that invented chunk ids are rejected.
