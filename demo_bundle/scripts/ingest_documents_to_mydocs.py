# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import re
from pathlib import Path
from uuid import uuid4

import pandas as pd
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document
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


class StructuredDataLoader:
    """Custom loader for structured data files (Excel, CSV) that preserves structure and metadata"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_ext = Path(file_path).suffix.lower()
    
    def load(self):
        """Load structured data file and convert to Document objects with rich metadata"""
        documents = []
        
        try:
            if self.file_ext == '.csv':
                return self._load_csv()
            elif self.file_ext == '.xlsx':
                return self._load_excel()
            else:
                raise ValueError(f"Unsupported file type: {self.file_ext}")
                
        except Exception as e:
            raise ValueError(f"Error loading {self.file_ext} file {self.file_path}: {str(e)}")
        
        return documents
    
    def _load_csv(self):
        """Load CSV file and convert to Document objects"""
        documents = []
        
        # Try different encodings for CSV files
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(self.file_path, encoding=encoding)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if df is None:
            raise ValueError("Could not read CSV file with any supported encoding")
        
        # Skip empty files
        if df.empty:
            return documents
        
        # Convert CSV to structured text content
        content_parts = []
        content_parts.append(f"CSV File: {Path(self.file_path).name}")
        content_parts.append("=" * 50)
        
        # Add column headers
        headers = df.columns.tolist()
        content_parts.append(f"Columns: {', '.join(map(str, headers))}")
        content_parts.append("")
        
        # Process each row with rich context
        for idx, row in df.iterrows():
            row_content = []
            row_content.append(f"Row {idx + 1}:")
            
            for col in headers:
                value = row[col]
                if pd.notna(value):
                    row_content.append(f"  {col}: {value}")
            
            content_parts.append("\n".join(row_content))
            content_parts.append("")
        
        # Create document with comprehensive metadata
        csv_content = "\n".join(content_parts)
        
        metadata = {
            "source": self.file_path,
            "file_type": "csv",
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": "|".join(map(str, headers)),
            "file_name": Path(self.file_path).name,
            "file_extension": self.file_ext
        }
        
        # Add summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            metadata["numeric_columns"] = "|".join(numeric_cols)
            metadata["has_numeric_data"] = True
        else:
            metadata["has_numeric_data"] = False
        
        # Add data type information
        dtype_info = []
        for col in headers:
            dtype_info.append(f"{col}:{str(df[col].dtype)}")
        metadata["column_types"] = "|".join(dtype_info)
        
        documents.append(Document(
            page_content=csv_content,
            metadata=metadata
        ))
        
        return documents
    
    def _load_excel(self):
        """Load Excel file and convert to Document objects"""
        documents = []
        
        # Read Excel file (.xlsx)
        excel_file = pd.ExcelFile(self.file_path, engine='openpyxl')
        
        # Process each sheet
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
            
            # Skip empty sheets
            if df.empty:
                continue
            
            # Convert sheet to structured text content
            content_parts = []
            content_parts.append(f"Sheet: {sheet_name}")
            content_parts.append("=" * 50)
            
            # Add column headers
            headers = df.columns.tolist()
            content_parts.append(f"Columns: {', '.join(map(str, headers))}")
            content_parts.append("")
            
            # Process each row with rich context
            for idx, row in df.iterrows():
                row_content = []
                row_content.append(f"Row {idx + 1}:")
                
                for col in headers:
                    value = row[col]
                    if pd.notna(value):
                        row_content.append(f"  {col}: {value}")
                
                content_parts.append("\n".join(row_content))
                content_parts.append("")
            
            # Create document with comprehensive metadata
            sheet_content = "\n".join(content_parts)
            
            metadata = {
                "source": self.file_path,
                "file_type": "excel",
                "sheet_name": sheet_name,
                "sheet_index": excel_file.sheet_names.index(sheet_name),
                "total_sheets": len(excel_file.sheet_names),
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": "|".join(map(str, headers)),  # Store as pipe-separated string
                "file_name": Path(self.file_path).name,
                "file_extension": self.file_ext
            }
            
            # Add summary statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                metadata["numeric_columns"] = "|".join(numeric_cols)
                metadata["has_numeric_data"] = True
            else:
                metadata["has_numeric_data"] = False
            
            # Add data type information
            dtype_info = []
            for col in headers:
                dtype_info.append(f"{col}:{str(df[col].dtype)}")
            metadata["column_types"] = "|".join(dtype_info)
            
            documents.append(Document(
                page_content=sheet_content,
                metadata=metadata
            ))
        
        return documents


def get_loader_for_file(file_path: str):
    """Get appropriate document loader based on file extension"""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == '.pdf':
        return PyPDFLoader(file_path)
    elif file_ext == '.docx':
        return Docx2txtLoader(file_path)
    elif file_ext in ['.xlsx', '.csv']:
        return StructuredDataLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}. Supported types: .pdf, .docx, .xlsx, .csv")


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
    parser = argparse.ArgumentParser(description="Ingest a document (PDF, DOCX, XLSX, CSV) into a Milvus collection for RAG")
    parser.add_argument("document", help="Path to the document file (PDF, DOCX, XLSX, or CSV)")
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
