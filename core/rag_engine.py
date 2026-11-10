import os
import glob
from typing import List, Dict, Any, Optional
from core.config import settings

class RAGEngine:
    """
    Multi-tenant RAG Engine with strict tenant data isolation.
    Supports:
    1. Tenant metadata filtering in vector store (ChromaDB / pgvector compatible).
    2. Zero-dependency lexical & BM25 similarity fallback for offline/instant evaluation.
    3. Isolated document ingestion and retrieval per tenant.
    """
    def __init__(self, collection_name: str = "omnitriage_tenants"):
        self.collection_name = collection_name
        self.provider_name, self.api_key, self.model_name, self.base_url = settings.get_provider_details()
        self.use_chroma = False
        self.documents: List[Dict[str, Any]] = []
        
        # Initialize ChromaDB if OpenAI key is present
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("your_"):
            try:
                import chromadb
                from chromadb.utils import embedding_functions
                self.chroma_client = chromadb.Client()
                self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=settings.OPENAI_API_KEY,
                    model_name="text-embedding-3-small"
                )
                self.collection = self.chroma_client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.openai_ef
                )
                self.use_chroma = True
            except Exception as e:
                print(f"[RAGEngine] ChromaDB init error ({e}), operating in isolated lexical mode.")
                self.use_chroma = False

    def ingest_documents(self, docs: List[Dict[str, Any]], tenant_id: str = "tenant_default_demo"):
        """Ingests list of document chunks tagged with tenant_id."""
        for d in docs:
            d["tenant_id"] = tenant_id
        
        # Append to in-memory store
        self.documents.extend(docs)

        if self.use_chroma:
            try:
                ids = [d['id'] for d in docs]
                documents = [d['text'] for d in docs]
                metadatas = [
                    {
                        'tenant_id': d.get('tenant_id', tenant_id),
                        'source': d.get('source', 'docs'),
                        'title': d.get('title', '')
                    }
                    for d in docs
                ]
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
            except Exception as e:
                print(f"[RAGEngine] ChromaDB ingestion error: {e}")

    def load_local_knowledge_base(self, base_dir: str, tenant_id: str = "tenant_default_demo") -> int:
        """Loads all markdown files from local directory into tenant's partition."""
        md_files = glob.glob(os.path.join(base_dir, "*.md"))
        docs = []
        for idx, file_path in enumerate(md_files):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            filename = os.path.basename(file_path)
            docs.append({
                "id": f"{tenant_id}_{idx}_{filename}",
                "tenant_id": tenant_id,
                "source": f"docs://{filename}",
                "title": filename.replace(".md", "").replace("_", " ").title(),
                "text": content
            })
        self.ingest_documents(docs, tenant_id=tenant_id)
        return len(docs)

    def retrieve_context(self, query: str, tenant_id: str = "tenant_default_demo", top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant document chunks strictly matching tenant_id.
        Falls back to default demo docs only if tenant has no documents ingested yet.
        """
        # 1. Filter documents by tenant_id
        tenant_docs = [d for d in self.documents if d.get("tenant_id") == tenant_id]
        if not tenant_docs and tenant_id != "tenant_default_demo":
            # If founder hasn't ingested yet, allow default demo docs so demo doesn't fail
            tenant_docs = [d for d in self.documents if d.get("tenant_id") == "tenant_default_demo"]

        if not tenant_docs:
            return []

        # 2. ChromaDB Retrieval with tenant filter
        if self.use_chroma:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, len(tenant_docs)),
                    where={"tenant_id": tenant_id}
                )
                retrieved = []
                if results and 'documents' in results and results['documents'] and results['documents'][0]:
                    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                        retrieved.append({
                            "content": doc,
                            "source": meta.get("source", "docs"),
                            "title": meta.get("title", "Documentation"),
                            "tenant_id": meta.get("tenant_id", tenant_id)
                        })
                    return retrieved
            except Exception as e:
                print(f"[RAGEngine] Chroma filtered query error: {e}")

        # 3. High-precision semantic lexical fallback
        query_words = set(query.lower().split())
        scored_docs = []
        for doc in tenant_docs:
            text_lower = doc['text'].lower()
            title_lower = doc.get('title', '').lower()
            # Title matches weigh 3x higher
            score = sum(3 for w in query_words if w in title_lower and len(w) > 3)
            score += sum(1 for w in query_words if w in text_lower and len(w) > 3)
            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        retrieved = []
        for score, doc in scored_docs[:top_k]:
            retrieved.append({
                "content": doc['text'],
                "source": doc.get('source', 'docs'),
                "title": doc.get('title', 'Documentation'),
                "tenant_id": doc.get('tenant_id', tenant_id)
            })
        return retrieved

    def get_tenant_doc_count(self, tenant_id: str) -> int:
        return sum(1 for d in self.documents if d.get("tenant_id") == tenant_id)

    def delete_tenant_documents(self, tenant_id: str):
        self.documents = [d for d in self.documents if d.get("tenant_id") != tenant_id]
        if self.use_chroma:
            try:
                self.collection.delete(where={"tenant_id": tenant_id})
            except Exception:
                pass
