import os
import chromadb
from backend.utils.embeddings import get_embeddings

class ChromaDB:
    def __init__(self, persist_directory="vector_db", embedding_function=None):

        self.persist_directory = os.path.abspath(persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.embeddings = embedding_function or get_embeddings()

        self.collection = None
        self.collection_name = "kb_collection"

    def build(self, documents):
        existing = [c.name for c in self.client.list_collections()]
        if self.collection_name in existing:
            self.client.delete_collection(self.collection_name)

        self.collection = self.client.create_collection(name=self.collection_name)

        texts = [doc.page_content for doc in documents]
        ids = [str(i) for i in range(len(texts))]
        metadatas = [doc.metadata or {} for doc in documents]

        vectors = self.embeddings.embed_documents(texts)
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=vectors,
            metadatas=metadatas,
        )

        return {"status": "success", "count": len(texts)}

    def load(self):
        self.collection = self.client.get_collection(self.collection_name)
        return self.collection

    def similarity_search(self, query, k=5):

        if self.collection is None:
            try:
                self.load()
            except Exception:
                return []

        q_emb = self.embeddings.embed_query(query)
        results = self.collection.query(query_embeddings=[q_emb], n_results=k)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        out = []
        for text, meta in zip(docs, metas):
            out.append({"text": text, "metadata": meta or {}})

        return out

    def add_texts(self, texts):
        if self.collection is None:
            self.load()

        ids = [f"extra-{i}" for i in range(len(texts))]
        vectors = self.embeddings.embed_documents(texts)
        self.collection.add(ids=ids, documents=texts, embeddings=vectors)

    def clear(self):
        existing = [c.name for c in self.client.list_collections()]
        if self.collection_name in existing:
            self.client.delete_collection(self.collection_name)
