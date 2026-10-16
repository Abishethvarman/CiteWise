"""Synthetic documents for the local demo. These are not judgments or statutes."""

import pymupdf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document
from app.services.index_store import IndexStore
from app.services.ingestion import accept_upload, ingest_document

DEMOS = [
    {
        "filename": "SYNTHETIC - Harbour and Co v Northwind Supplies.pdf",
        "jurisdiction": "Synthetic — not a real jurisdiction",
        "pages": [
            "\n".join(
                [
                    "SYNTHETIC DEMO DOCUMENT. This is not a judgment and not legal advice.",
                    "Harbour and Co v Northwind Supplies",
                    "The buyer Harbour and Co ordered oak timber from Northwind Supplies.",
                    "Northwind delivered the oak timber twelve days after the contractual date.",
                    "Harbour and Co withheld payment and alleged late delivery of timber.",
                    "The court recorded that the contract named 14 March as the delivery date.",
                ]
            ),
            "\n".join(
                [
                    "SYNTHETIC DEMO DOCUMENT. Page 2. This is not a judgment.",
                    "The measure of loss is the difference between the contract price and the market price on the delivery date.",
                    "The court assessed damages for the late timber at that difference.",
                    "Nothing in this synthetic judgment discusses cryptocurrency wallets or satellite spectrum licensing.",
                    "Costs follow the event unless the court orders otherwise in this synthetic judgment.",
                ]
            ),
        ],
    },
    {
        "filename": "SYNTHETIC - Example Evidence Act 2024.pdf",
        "jurisdiction": "Synthetic — not a real jurisdiction",
        "pages": [
            "\n".join(
                [
                    "SYNTHETIC DEMO DOCUMENT. This is not a statute and not the law of any place.",
                    "Example Evidence Act 2024, section 14.",
                    "A business record may be admitted when the witness who made it is unavailable.",
                    "The record must have been made in the course of regularly conducted activity.",
                    "This section is fictional text created so CiteWise can demonstrate quotations.",
                ]
            ),
            "\n".join(
                [
                    "SYNTHETIC DEMO DOCUMENT. Page 2 of the fictional Example Evidence Act.",
                    "Section 15. A witness is unavailable if the witness cannot be found after a reasonable search.",
                    "The fictional act does not mention timber prices or Northwind Supplies.",
                ]
            ),
        ],
    },
]


def build_pdf(pages: list[str]) -> bytes:
    document = pymupdf.open()
    try:
        for body in pages:
            page = document.new_page(width=595, height=842)
            y = 72
            for line in body.split("\n"):
                page.insert_text((72, y), line[:110], fontsize=11, fontname="helv")
                y += 18
        return document.tobytes()
    finally:
        document.close()


def seed_demo(
    db: Session, settings: Settings, index_store: IndexStore
) -> tuple[list[Document], int, int]:
    created = 0
    present = 0
    documents: list[Document] = []
    for spec in DEMOS:
        existing = db.scalar(
            select(Document).where(
                Document.filename == spec["filename"], Document.synthetic.is_(True)
            )
        )
        if existing is not None:
            present += 1
            documents.append(existing)
            continue
        data = build_pdf(spec["pages"])
        document = accept_upload(
            db,
            settings,
            filename=spec["filename"],
            content_type="application/pdf",
            data=data,
            jurisdiction=spec["jurisdiction"],
            synthetic=True,
        )
        ingest_document(db, settings, index_store, document.id)
        db.refresh(document)
        documents.append(document)
        created += 1
    return documents, created, present
