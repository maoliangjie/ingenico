# Upload Management Module

## What it implements
- Upload persistence under `storage/uploads/`
- Upload metadata registry in `storage/uploads.json`
- API operations for create, list, replace, and delete

## What it solves
- Adds dynamic knowledge management without introducing object storage
- Keeps uploaded files inspectable and locally persistent
- Synchronizes retrieval state after upload changes

## Technologies used
- FastAPI multipart uploads
- Local filesystem storage
- JSON metadata manifests with simple locking

## How it interacts with other modules
- `app/services/upload_store.py` owns file persistence and metadata bookkeeping
- `app/services/rag_service.py` refreshes the retrieval index after upload mutations
- `frontend/` exposes the upload lifecycle in the operator console
- Verification scripts and Postman assets cover upload, replace, and delete flows
