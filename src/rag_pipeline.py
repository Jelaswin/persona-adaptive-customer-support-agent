import os
import logging
from typing import List, Dict, Any
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import pypdf

from src.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


class RAGPipeline:
    def __init__(self):
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()

        db_path = os.path.abspath(settings.CHROMA_DB_PATH)
        os.makedirs(db_path, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " ", ""],
        )

        self._kb_loaded = False

    def load_knowledge_base(self, force: bool = False) -> int:
        if self._kb_loaded and not force:
            return self.collection.count()

        kb_dir = Path(settings.KB_DIR)
        if not kb_dir.exists():
            logger.warning("Knowledge base directory not found: %s", kb_dir)
            return 0

        existing_count = self.collection.count()
        if existing_count > 0 and not force:
            logger.info(
                "Collection already has %d documents. Skipping load.", existing_count
            )
            self._kb_loaded = True
            return existing_count

        if force and existing_count > 0:
            logger.info("Forcing reload - deleting existing collection data.")
            self.chroma_client.delete_collection(settings.CHROMA_COLLECTION_NAME)
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

        documents = []
        metadatas = []
        ids = []
        doc_id_counter = 0

        for file_path in kb_dir.iterdir():
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            text = self._read_file(file_path)
            if not text.strip():
                logger.warning("Skipping empty file: %s", file_path.name)
                continue

            chunks = self.text_splitter.split_text(text)

            for chunk in chunks:
                doc_id_counter += 1
                chunk_id = f"doc_{doc_id_counter}"
                documents.append(chunk)
                metadatas.append({
                    "source": file_path.name,
                    "source_type": file_path.suffix.lower().lstrip("."),
                    "chunk_index": doc_id_counter,
                })
                ids.append(chunk_id)

        if not documents:
            logger.warning("No documents found in knowledge base.")
            return 0

        logger.info("Generating embeddings for %d chunks...", len(documents))
        embeddings = self._generate_embeddings(documents)

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        self._kb_loaded = True
        count = self.collection.count()
        logger.info("Knowledge base loaded: %d chunks from %d source files.", count, doc_id_counter)
        return count

    def query(self, query_text: str, k: int = None) -> Dict[str, Any]:
        if k is None:
            k = settings.TOP_K_RETRIEVAL

        try:
            query_embedding = self._generate_embedding(query_text)
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            return {
                "results": [],
                "query": query_text,
                "error": str(e),
            }

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("ChromaDB query failed: %s", e)
            return {
                "results": [],
                "query": query_text,
                "error": str(e),
            }

        retrieved = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0.0
                confidence = max(0.0, 1.0 - distance)
                retrieved.append({
                    "content": doc,
                    "source": results["metadatas"][0][i]["source"],
                    "source_type": results["metadatas"][0][i]["source_type"],
                    "distance": round(distance, 4),
                    "confidence": round(confidence, 4),
                })

        return {
            "results": retrieved,
            "query": query_text,
            "error": None,
        }

    def retrieval_confidence(self, results: List[Dict]) -> float:
        if not results:
            return 0.0
        return max(r["confidence"] for r in results)

    def _read_file(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return self._read_pdf(file_path)
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="latin-1")

    @staticmethod
    def _read_pdf(file_path: Path) -> str:
        text_parts = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
        except Exception as e:
            logger.error("Failed to read PDF %s: %s", file_path.name, e)
        return "\n".join(text_parts)

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.encode(texts, show_progress_bar=False).tolist()

    def _generate_embedding(self, text: str) -> List[float]:
        return self.embedder.encode(text).tolist()

    def get_collection_stats(self) -> Dict[str, Any]:
        return {
            "document_count": self.collection.count(),
            "collection_name": settings.CHROMA_COLLECTION_NAME,
        }
