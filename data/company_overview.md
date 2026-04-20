# Ingenico Local Knowledge Base

Ingenico's stage-1 assistant helps internal users answer questions from local project documents.

The MVP supports only text, markdown, and JSON files placed inside the `/data` directory.

The backend stores retrieval state in Chroma and conversation history in SQLite.

Docker Compose is the preferred way to boot the service for repeatable local development.
