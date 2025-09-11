# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import re
from pathlib import Path
from uuid import uuid4

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings


def clean_metadata_for_milvus(metadata: dict) -> dict:
    """Clean metadata field names to be compatible with Milvus.
    
    Milvus field names can only contain numbers, letters, and underscores.
    This function converts invalid characters to underscores.
    """
    cleaned = {}
    for key, value in metadata.items():
        # Replace any non-alphanumeric characters (except underscore) with underscore
        clean_key = re.sub(r'[^a-zA-Z0-9_]', '_', str(key))
        # Remove leading/trailing underscores and collapse multiple underscores
        clean_key = re.sub(r'_+', '_', clean_key).strip('_')
        # Ensure key doesn't start with a number (prepend 'field_' if it does)
        if clean_key and clean_key[0].isdigit():
            clean_key = f'field_{clean_key}'
        # Use 'unknown_field' if key becomes empty after cleaning
        if not clean_key:
            clean_key = 'unknown_field'
        cleaned[clean_key] = value
    return cleaned


def get_loader_for_file(file_path: str):
    """Get appropriate document loader based on file extension"""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == '.pdf':
        return PyPDFLoader(file_path)
    elif file_ext == '.docx':
        try:
            return Docx2txtLoader(file_path)
        except ImportError:
            print("Warning: docx2txt not available, trying UnstructuredWordDocumentLoader")
            return UnstructuredWordDocumentLoader(file_path)
    elif file_ext == '.doc':
        return UnstructuredWordDocumentLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}. Supported types: .pdf, .doc, .docx")


def ingest_document(
    doc_path: str,
    *,
    milvus_uri: str = "http://localhost:19530",
    collection_name: str = "my_docs",
    model: str = "nvidia/nv-embedqa-e5-v5",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> int:
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"Document not found: {doc_path}")

    # Get appropriate loader for the file type
    loader = get_loader_for_file(doc_path)
    
    # Load and split document
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents(docs)

    # Clean metadata field names to be compatible with Milvus
    for doc in docs:
        if doc.metadata:
            doc.metadata = clean_metadata_for_milvus(doc.metadata)

    print(f"Loaded {len(docs)} chunks from {doc_path}")
    
    # Create embedder and vector store
    embedder = NVIDIAEmbeddings(model=model, truncate="END")
    vector_store = Milvus(
        embedding_function=embedder,
        collection_name=collection_name,
        connection_args={"uri": milvus_uri},
    )

    ids = [str(uuid4()) for _ in range(len(docs))]
    inserted_ids = vector_store.add_documents(docs, ids=ids)
    return len(inserted_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a document (PDF, DOC, DOCX) into a Milvus collection for RAG")
    parser.add_argument("document", help="Path to the document file (PDF, DOC, or DOCX)")
    parser.add_argument("--uri", default=os.getenv("MILVUS_URI", "http://localhost:19530"), help="Milvus URI")
    parser.add_argument(
        "--collection", default=os.getenv("MILVUS_COLLECTION", "my_docs"), help="Milvus collection name"
    )
    parser.add_argument(
        "--model",
        default=os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5"),
        help="Embedding model name",
    )
    parser.add_argument("--chunk_size", type=int, default=1000, help="Chunk size for splitting")
    parser.add_argument("--chunk_overlap", type=int, default=200, help="Chunk overlap for splitting")
    args = parser.parse_args()

    try:
        count = ingest_document(
            args.document,
            milvus_uri=args.uri,
            collection_name=args.collection,
            model=args.model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print(f"Successfully ingested {count} chunks into collection '{args.collection}'")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
