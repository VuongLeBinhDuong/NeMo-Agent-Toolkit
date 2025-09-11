# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os

try:
    from pymilvus.milvus_client import MilvusClient
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "pymilvus is required. Install with: .venv\\Scripts\\python.exe -m pip install pymilvus"
    ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Drop a Milvus collection by name")
    parser.add_argument("--uri", default=os.getenv("MILVUS_URI", "http://localhost:19530"), help="Milvus URI")
    parser.add_argument(
        "--collection", default=os.getenv("MILVUS_COLLECTION", "my_docs"), help="Collection name to drop"
    )
    args = parser.parse_args()

    client = MilvusClient(uri=args.uri)
    before = client.list_collections()
    print("Collections before:", before)

    if args.collection in before:
        client.drop_collection(args.collection)
        print(f"Dropped collection '{args.collection}'")
    else:
        print(f"Collection '{args.collection}' not found. Nothing to drop.")

    after = client.list_collections()
    print("Collections after:", after)


if __name__ == "__main__":
    main()


