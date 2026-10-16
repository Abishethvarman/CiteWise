# Screenshots

Captured on 16 October 2026 from a local CiteWise run in the browser. Every document visible in these images is from the synthetic demo set. The files are fictional and are labelled SYNTHETIC in the application.

- `landing.png` — landing page, with the tagline and the link into the workspace.
- `library.png` — library filtered to the synthetic demo, including the upload form.
- `research.png` — search for “oak timber contractual date”. The Northwind page is ranked first.
- `viewer.png` — PDF page 1 of the synthetic Harbour and Co v Northwind Supplies file, including the twelve-days sentence.
- `answer.png` — the same question sent to local Ollama (`llama3.2:3b`). The model answered “Not specified”. CiteWise marked the answer insufficient and did not invent a quotation. The retrieved passage above the answer still contains the twelve-days sentence. That gap is a model-quality limit, not a citation the application accepted.
- `verification.png` — citation check for that answer. There are no evidence items to check, because the model did not cite a passage. The page states that a source match is not legal correctness.
- `settings.png` — local inference mode, Ollama `0.6.6`, model `llama3.2:3b`, embeddings `nomic-embed-text`, and the statement that no commercial API is used. The data directory shown is the path on the machine where the screenshot was taken.
