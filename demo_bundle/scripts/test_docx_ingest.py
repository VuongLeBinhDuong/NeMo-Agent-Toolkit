# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import re
from pathlib import Path
from uuid import uuid4

from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

def clean_metadata_for_milvus(metadata: dict) -> dict:
    """Clean metadata field names to be compatible with Milvus."""
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
        
        # Convert value to string if it's not already
        if not isinstance(value, (str, int, float, bool)):
            value = str(value)
            
        cleaned[clean_key] = value
    return cleaned

def test_docx_ingest(
    docx_path: str,
    milvus_uri: str = "http://localhost:19530",
    collection_name: str = "test_docx",
    model: str = "nvidia/nv-embedqa-e5-v5"
):
    print(f"=== Testing DOCX ingest: {docx_path} ===")
    
    # Load DOCX
    loader = Docx2txtLoader(docx_path)
    docs = loader.load()
    print(f"Loaded {len(docs)} documents")
    
    # Split documents
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = splitter.split_documents(docs)
    print(f"Split into {len(docs)} chunks")
    
    # Clean metadata
    for doc in docs:
        if doc.metadata:
            original_metadata = doc.metadata.copy()
            doc.metadata = clean_metadata_for_milvus(doc.metadata)
            print(f"Metadata cleaned: {original_metadata} -> {doc.metadata}")
    
    # Try to drop existing test collection
    try:
        from pymilvus.milvus_client import MilvusClient
        client = MilvusClient(uri=milvus_uri)
        if collection_name in client.list_collections():
            client.drop_collection(collection_name)
            print(f"Dropped existing collection '{collection_name}'")
    except Exception as e:
        print(f"Warning: Could not check/drop existing collection: {e}")
    
    # Create embedder and vector store
    print("Creating embedder...")
    embedder = NVIDIAEmbeddings(model=model, truncate="END")
    
    print("Creating Milvus vector store...")
    vector_store = Milvus(
        embedding_function=embedder,
        collection_name=collection_name,
        connection_args={"uri": milvus_uri},
    )
    
    # Generate IDs and try to insert
    print("Generating IDs and inserting documents...")
    ids = [str(uuid4()) for _ in range(len(docs))]
    
    try:
        inserted_ids = vector_store.add_documents(docs, ids=ids)
        print(f"✓ Successfully inserted {len(inserted_ids)} documents!")
        return len(inserted_ids)
    except Exception as e:
        print(f"✗ Failed to insert documents: {e}")
        print(f"Error type: {type(e)}")
        
        # Show problematic document info
        if docs:
            print("Sample document that failed:")
            sample = docs[0]
            print(f"  Content length: {len(sample.page_content)}")
            print(f"  Metadata: {sample.metadata}")
            print(f"  Content preview: {sample.page_content[:200]}...")
        
        return 0

def main():
    parser = argparse.ArgumentParser(description="Test DOCX ingest to Milvus")
    parser.add_argument("docx_file", help="Path to DOCX file")
    parser.add_argument("--uri", default="http://localhost:19530", help="Milvus URI")
    parser.add_argument("--collection", default="test_docx", help="Collection name")
    args = parser.parse_args()
    
    if not os.path.exists(args.docx_file):
        print(f"File not found: {args.docx_file}")
        return 1
    
    try:
        count = test_docx_ingest(args.docx_file, args.uri, args.collection)
        if count > 0:
            print(f"SUCCESS: Ingested {count} chunks from DOCX")
            return 0
        else:
            print("FAILED: No documents were ingested")
            return 1
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
