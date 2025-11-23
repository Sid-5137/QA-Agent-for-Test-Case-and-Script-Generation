import os
from backend.utils.parsers import load_documents
from backend.utils.embeddings import get_embeddings
from backend.vector_store.chroma_store import ChromaDB


class IngestionAgent:

    def ingest(self, docs_path: str):
        docs_path = os.path.abspath(docs_path)

        if not os.path.exists(docs_path):
            return {"status": "error", "message": "docs_path not found"}

        file_paths = []
        for f in os.listdir(docs_path):
            full = os.path.join(docs_path, f)

            # skip folders, vector store dirs, cache dirs etc
            if os.path.isdir(full):
                continue

            if f.lower().endswith((".md", ".txt", ".json", ".html", ".pdf")):
                file_paths.append(full)

        if not file_paths:
            return {"status": "error", "message": "no valid files found"}

        # Load + chunk to Document objects
        docs = load_documents(file_paths)
        if not docs:
            return {"status": "error", "message": "document loading failed"}

        # Build Vector DB
        embeddings = get_embeddings()
        db_path = os.path.join(docs_path, "vector_db")

        db = ChromaDB(persist_directory=db_path, embedding_function=embeddings)
        result = db.build(docs)

        return {
            "status": "success",
            "message": "Knowledge base built successfully",
            "docs_path": docs_path,
            "total_documents": len(file_paths),
            "total_chunks": result.get("count", 0),
            "vector_db_path": db_path
        }
