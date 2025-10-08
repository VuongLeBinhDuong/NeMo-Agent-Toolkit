# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import re
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        cleaned[clean_key] = value
    return cleaned

def debug_docx_loading(file_path: str):
    """Debug DOCX loading and show metadata"""
    print(f"=== Debugging DOCX file: {file_path} ===")
    
    # Try Docx2txtLoader first
    try:
        print("Trying Docx2txtLoader...")
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        print(f"✓ Docx2txtLoader successful! Loaded {len(docs)} documents")
        
        for i, doc in enumerate(docs):
            print(f"  Document {i}:")
            print(f"    Content length: {len(doc.page_content)}")
            print(f"    Original metadata: {doc.metadata}")
            cleaned_metadata = clean_metadata_for_milvus(doc.metadata)
            print(f"    Cleaned metadata: {cleaned_metadata}")
            print(f"    Content preview: {doc.page_content[:200]}...")
            print()
            
    except Exception as e:
        print(f"✗ Docx2txtLoader failed: {e}")
        
        # Try UnstructuredWordDocumentLoader as fallback
        try:
            print("Trying UnstructuredWordDocumentLoader...")
            loader = UnstructuredWordDocumentLoader(file_path)
            docs = loader.load()
            print(f"✓ UnstructuredWordDocumentLoader successful! Loaded {len(docs)} documents")
            
            for i, doc in enumerate(docs):
                print(f"  Document {i}:")
                print(f"    Content length: {len(doc.page_content)}")
                print(f"    Original metadata: {doc.metadata}")
                cleaned_metadata = clean_metadata_for_milvus(doc.metadata)
                print(f"    Cleaned metadata: {cleaned_metadata}")
                print(f"    Content preview: {doc.page_content[:200]}...")
                print()
                
        except Exception as e2:
            print(f"✗ UnstructuredWordDocumentLoader also failed: {e2}")
            return None
    
    # Test text splitting
    print("Testing text splitting...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = splitter.split_documents(docs)
    print(f"✓ Split into {len(split_docs)} chunks")
    
    # Clean metadata for all chunks
    for doc in split_docs:
        if doc.metadata:
            doc.metadata = clean_metadata_for_milvus(doc.metadata)
    
    print("Sample chunk after splitting:")
    if split_docs:
        sample = split_docs[0]
        print(f"  Content: {sample.page_content[:200]}...")
        print(f"  Metadata: {sample.metadata}")
    
    return split_docs

def main():
    parser = argparse.ArgumentParser(description="Debug DOCX file loading")
    parser.add_argument("docx_file", help="Path to DOCX file")
    args = parser.parse_args()
    
    if not os.path.exists(args.docx_file):
        print(f"File not found: {args.docx_file}")
        return 1
    
    debug_docx_loading(args.docx_file)
    return 0

if __name__ == "__main__":
    exit(main())
