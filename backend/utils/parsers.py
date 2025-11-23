from pathlib import Path

from langchain_community.document_loaders import (
    UnstructuredMarkdownLoader,
    TextLoader,
    JSONLoader,
    UnstructuredHTMLLoader,
    PyMuPDFLoader,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_documents(file_paths):
    """Load and chunk multiple document types for RAG ingestion."""
    docs = []
    for path in file_paths:
        if path.endswith(".md"):
            loader = UnstructuredMarkdownLoader(path)

        elif path.endswith(".txt"):
            loader = TextLoader(path)

        elif path.endswith(".json"):
            loader = JSONLoader(
                file_path=path,
                jq_schema=".",
                text_content=False,
            )

        elif path.endswith(".html"):
            loader = UnstructuredHTMLLoader(path)

        elif path.endswith(".pdf"):
            loader = PyMuPDFLoader(path)

        else:
            raise ValueError(f"Unsupported file format: {path}")

        docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
    split_docs = splitter.split_documents(docs)

    for doc in split_docs:
        source_path = doc.metadata.get("source") or "unknown"
        doc.metadata.setdefault("source_document", Path(source_path).name)

    return split_docs
