# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
from uuid import uuid4

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings


def ingest_pdf(
    pdf_path: str,
    *,
    milvus_uri: str = "http://localhost:19530",
    collection_name: str = "my_docs",
    model: str = "nvidia/nv-embedqa-e5-v5",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> int:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Load and split document
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents(docs)

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
    parser = argparse.ArgumentParser(description="Ingest a PDF into a Milvus collection for RAG")
    parser.add_argument("pdf", help="Path to the PDF file")
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

    count = ingest_pdf(
        args.pdf,
        milvus_uri=args.uri,
        collection_name=args.collection,
        model=args.model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(f"Ingested {count} chunks into collection '{args.collection}'")


if __name__ == "__main__":
    main()


