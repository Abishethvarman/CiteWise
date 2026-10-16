# Security policy

CiteWise 0.1 is a trusted single-user local application. It is not a multi-tenant production legal platform.

## Reporting

If this repository is published on GitHub, use a private security advisory. Until then, report problems privately to the maintainers of your copy. Do not open a public issue that includes uploaded document text, session contents, or a working exploit.

## What this release does

- Stores uploads under a configured data directory using generated ids, not the original filename, as the path.
- Checks the extension, declared MIME type, PDF signature, size, and page count.
- Uses SQLAlchemy for database queries.
- Treats extracted text as untrusted data in the model prompt and fences a few closing tags. That is not a guarantee against prompt injection.
- Does not execute commands found in documents and does not give the model a shell or network tool.
- Does not send documents to a commercial model API.
- Restricts browser CORS to configured origins.
- Deletes the stored PDF, page rows, chunk rows, and index entries when a document is deleted.

## What this release does not do

- It does not authenticate users. Do not expose it on a network where other people can reach it unless you add authentication and access control first.
- It does not encrypt the database or the upload directory.
- It does not stop someone with access to the computer from reading the data directory.
- It does not claim to prevent all prompt injection. A hostile document can still influence a model that ignores the system prompt. Verification can flag citations that do not resolve; it cannot make the model honest.
- Local processing does not secure the operating system, the Ollama port, or backups.

## Supported scope

Report issues in the application code of this repository. Model weights and Ollama itself are separate projects with their own licences and security processes.
