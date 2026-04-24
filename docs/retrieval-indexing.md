# Retrieval and Indexing Module

## What it implements
- Source discovery across static `data/` and dynamic `storage/uploads/`
- Text, markdown, JSON, and text-based PDF ingestion
- Chroma index creation, manifest tracking, and rebuild decisions

## What it solves
- Keeps retrieval grounded in local project data
- Prevents stale indexes by hashing source content plus embedding configuration
- Lets uploaded files participate in retrieval without changing the core RAG flow
- Skips static PDFs that are unreadable or contain no extractable text instead of failing startup

## Technologies used
- LangChain document abstractions
- Recursive character splitting
- Chroma persistent vector storage
- Local Hugging Face embeddings or OpenAI-compatible embeddings
- `pypdf` for minimum-viable PDF text extraction

## How it interacts with other modules
- `app/services/document_loader.py` provides document loading and fingerprints
- `app/services/rag_service.py` owns rebuild logic and retrieval calls
- `app/services/upload_store.py` feeds dynamic files into the indexed source set
- Health reporting exposes document and chunk counts back through the API layer
- PDF extraction errors become warnings for static files and validation errors for uploaded files
