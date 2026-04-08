"""Utilities for connecting to the persistent Chroma vector store."""

from __future__ import annotations

import os

import chromadb
from chromadb.api.models.Collection import Collection
from dotenv import load_dotenv

COLLECTION_NAME = "reaction_commerce"


def _get_chroma_path() -> str:
    load_dotenv()
    return os.getenv("CHROMA_PATH", "./chroma_data")


def get_chroma_client() -> chromadb.PersistentClient:
    """Return a Chroma persistent client bound to the configured path."""
    return chromadb.PersistentClient(path=_get_chroma_path())


def get_collection() -> Collection:
    """Return the persistent Reaction Commerce collection, creating it if needed."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)
