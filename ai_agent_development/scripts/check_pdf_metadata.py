import argparse
from langchain_community.document_loaders import PyPDFLoader

def check_pdf_metadata(pdf_path):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    if docs:
        print(f"PDF metadata from {pdf_path}:")
        for key, value in docs[0].metadata.items():
            print(f"  {key}: {value}")
        print()
        print("All unique metadata keys across all pages:")
        all_keys = set()
        for doc in docs:
            all_keys.update(doc.metadata.keys())
        for key in sorted(all_keys):
            print(f"  - {key}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_file", help="PDF file to check")
    args = parser.parse_args()
    check_pdf_metadata(args.pdf_file)
