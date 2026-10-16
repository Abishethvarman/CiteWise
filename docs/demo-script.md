# CiteWise demonstration script

Use the synthetic documents created by the app. Do not upload a real client file for a public demo.

1. Start Ollama, the API, and the web app using the commands in the README.
2. Open the workspace. If the library is empty, choose **Load synthetic demo**. The files are labelled synthetic. They are not judgments or statutes.
3. Open **Library** and confirm both demo PDFs show a page count, a ready status, and a user-supplied jurisdiction of "Synthetic — not a real jurisdiction".
4. Open **Research**. Select `SYNTHETIC - Harbour and Co v Northwind Supplies.pdf`.
5. Search for `market price on the delivery date`. Open the passage. It should be PDF page 2.
6. Ask: `What measure of loss does the synthetic judgment use for the late timber?` Inspect the answer, the chunk id, and the evidence card. Open the page from the evidence card.
7. Open **Citation check**. Read the status. "Source text matched" means the quotation was found in the extract. It does not mean the proposition is legally correct.
8. Export the Markdown report and confirm it lists the document name, page, quotation, and status.
9. Ask: `What did the court hold about cryptocurrency wallets?` The documents do not discuss that. The result should be an insufficient-evidence response, or retrieved passages that the answer refuses to treat as support.
10. Open **Settings** and read the inference mode. It should name the local Ollama model when that service is running, or say the model service is unavailable. It should not claim that a commercial API was used.

If Ollama is not running, steps 6 and 9 still show retrieved passages and a clear unavailable-model status. That is the intended fallback. It is not a generated legal answer.
