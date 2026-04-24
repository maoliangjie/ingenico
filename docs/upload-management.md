# Upload Management Module

## What it implements
- Upload persistence under `storage/uploads/`
- Upload metadata registry in `storage/uploads.json`
- API operations for create, list, replace, and delete
- Upload validation for `.txt`, `.md`, `.json`, and text-based `.pdf`

## What it solves
- Adds dynamic knowledge management without introducing object storage
- Keeps uploaded files inspectable and locally persistent
- Synchronizes retrieval state after upload changes
- Rejects PDFs that cannot produce extractable text, preventing false-success uploads

## Technologies used
- FastAPI multipart uploads
- Local filesystem storage
- JSON metadata manifests with simple locking
- `pypdf` for minimal text extraction from uploaded PDFs

## How it interacts with other modules
- `app/services/upload_store.py` owns file persistence and metadata bookkeeping
- `app/services/rag_service.py` refreshes the retrieval index after upload mutations
- `frontend/` exposes the upload lifecycle in the operator console
- Verification scripts and Postman assets cover upload, replace, and delete flows
- PDF uploads share the same lifecycle, but require extractable text and do not include OCR
