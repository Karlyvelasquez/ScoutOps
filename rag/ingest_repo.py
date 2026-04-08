"""Ingests Reaction Commerce plugin files into a Chroma collection for RAG retrieval."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

if __package__ is None or __package__ == "":
    # Allow execution via `python rag/ingest_repo.py` from repo root.
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from rag.embeddings import embed_text
from rag.vector_store import get_collection

REACTION_REPO_URL = "https://github.com/reactioncommerce/reaction"
DEFAULT_LOCAL_REPO_DIR = Path("./data/reaction_commerce")
TOKEN_PATTERN = re.compile(r"\S+")
SUPPORTED_EXTENSIONS = {".js", ".graphql"}
SUPPORTED_FILENAMES = {"README.md"}
CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50


def _iter_plugin_dirs(repo_root: Path) -> Iterable[Path]:
    packages_dir = repo_root / "packages"
    if not packages_dir.exists():
        return []

    return sorted(path for path in packages_dir.glob("api-plugin-*") if path.is_dir())


def _is_supported_file(file_path: Path) -> bool:
    if file_path.name in SUPPORTED_FILENAMES:
        return True
    return file_path.suffix in SUPPORTED_EXTENSIONS


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def _chunks_from_tokens(tokens: list[str], chunk_size: int, overlap: int) -> list[str]:
    if not tokens:
        return []

    if overlap >= chunk_size:
        overlap = max(0, chunk_size - 1)

    step = max(1, chunk_size - overlap)
    chunks: list[str] = []

    for start in range(0, len(tokens), step):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        if not chunk_tokens:
            continue
        chunks.append(" ".join(chunk_tokens))
        if end >= len(tokens):
            break

    return chunks


def _chunk_file_text(text: str) -> list[str]:
    return _chunks_from_tokens(
        tokens=_tokenize(text),
        chunk_size=CHUNK_SIZE_TOKENS,
        overlap=CHUNK_OVERLAP_TOKENS,
    )


def _ensure_repo(local_repo_path: Path) -> Path:
    if local_repo_path.exists() and (local_repo_path / ".git").exists():
        return local_repo_path

    local_repo_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning Reaction Commerce into {local_repo_path} ...")
    subprocess.run(["git", "clone", REACTION_REPO_URL, str(local_repo_path)], check=True)
    return local_repo_path


def _make_chunk_id(plugin_name: str, file_path: Path, chunk_index: int) -> str:
    raw = f"{plugin_name}:{file_path.as_posix()}:{chunk_index}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"chunk_{digest}"


def ingest_reaction_repo() -> None:
    """Read plugin files, chunk them, embed chunks, and upsert into Chroma."""
    load_dotenv()

    configured_repo_path = os.getenv("REACTION_COMMERCE_REPO_PATH", "").strip()
    local_repo = Path(configured_repo_path) if configured_repo_path else DEFAULT_LOCAL_REPO_DIR
    repo_root = _ensure_repo(local_repo)

    collection = get_collection()
    plugin_dirs = list(_iter_plugin_dirs(repo_root))

    if not plugin_dirs:
        print("No plugin directories found under packages/api-plugin-* .")
        return

    total_chunks = 0
    for plugin_dir in plugin_dirs:
        plugin_name = plugin_dir.name
        print(f"Processing plugin: {plugin_name}")

        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, str]] = []
        ids: list[str] = []

        files = sorted(path for path in plugin_dir.rglob("*") if path.is_file() and _is_supported_file(path))

        for file_path in files:
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = file_path.read_text(encoding="latin-1", errors="ignore")
            except OSError as exc:
                print(f"  Skipping unreadable file {file_path}: {exc}")
                continue

            chunks = _chunk_file_text(text)
            relative_path = file_path.relative_to(repo_root)
            file_type = file_path.suffix.lstrip(".") if file_path.suffix else file_path.name

            for index, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                metadata = {
                    "plugin_name": plugin_name,
                    "file_path": relative_path.as_posix(),
                    "file_type": file_type,
                }
                chunk_id = _make_chunk_id(plugin_name, relative_path, index)

                documents.append(chunk)
                embeddings.append(embed_text(chunk))
                metadatas.append(metadata)
                ids.append(chunk_id)

        if documents:
            collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        total_chunks += len(documents)
        print(f"  Indexed {len(documents)} chunks from {plugin_name}")

    print(f"Ingestion complete. Total indexed chunks: {total_chunks}")


if __name__ == "__main__":
    ingest_reaction_repo()
