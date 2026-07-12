"""Load .txt poison-test documents into tech-trends-chatbot Redis vector index."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4


def _ensure_backend_on_path(backend: Path) -> None:
    sys.path.insert(0, str(backend))
    os.chdir(backend)


async def _load_txt_dir(docs_dir: Path) -> None:
    from tqdm import tqdm

    from app.config import settings
    from app.db import add_chunks_to_vector_db, get_redis, setup_db
    from app.openai import get_embeddings, token_size
    from app.utils.splitter import TextSplitter

    docs = []
    for filename in sorted(docs_dir.glob("*.txt")):
        text = filename.read_text(encoding="utf-8")
        docs.append((filename.stem, text))
    if not docs:
        print(f"no txt files in {docs_dir}")
        return

    chunks = []
    splitter = TextSplitter(chunk_size=512, chunk_overlap=150)
    for doc_name, doc_text in docs:
        doc_id = str(uuid4())[:8]
        for chunk_idx, chunk_text in enumerate(splitter.split(doc_text)):
            chunks.append({
                "chunk_id": f"{doc_id}:{chunk_idx + 1:04}",
                "text": chunk_text,
                "doc_name": doc_name,
                "vector": None,
            })

    vectors = []
    batch_size = 32
    with tqdm(total=len(chunks), desc="embedding") as pbar:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_vectors = await get_embeddings([c["text"] for c in batch])
            vectors.extend(batch_vectors)
            pbar.update(len(batch))

    for chunk, vector in zip(chunks, vectors):
        chunk["vector"] = vector

    async with get_redis() as rdb:
        await setup_db(rdb)
        await add_chunks_to_vector_db(rdb, chunks)
    print(f"loaded {len(chunks)} chunks from {len(docs)} txt docs (dir={docs_dir})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="", help="path to tech-trends backend dir")
    parser.add_argument("--docs-dir", default="", help="directory containing .txt files")
    args = parser.parse_args()
    backend = Path(args.backend) if args.backend else Path.cwd()
    docs_dir = Path(args.docs_dir) if args.docs_dir else backend / "data" / "docs"
    _ensure_backend_on_path(backend)
    asyncio.run(_load_txt_dir(docs_dir))


if __name__ == "__main__":
    main()
