"""RangeDocuments that copies a template into `ranges/<id>/documents/` of the home folder."""

import dataclasses
import shutil
from pathlib import Path
from typing import Sequence
from uuid import UUID

import yaml

from attack_range.application.cyber_range import CyberRange, CyberRangeError, Document
from attack_range.application.range_documents import RangeDocuments
from attack_range.domain.entities.common import Provider

from .file_cyber_range_repository import (
    SUFFIXES,
    USER_DATA_DIR,
    FileCyberRangeRepository,
    bootstrap_names,
    document_files,
    user_data_dir,
)
from .home import AttackRangeHome


class FileRangeDocuments(RangeDocuments):
    def __init__(self, home: AttackRangeHome, repository: FileCyberRangeRepository) -> None:
        self._home = home
        self._repository = repository

    def import_documents(self, range_id: UUID, source: Path) -> None:
        """Copy the YAML files and the user-data files they reference. Other files stay behind."""
        target = self._home.documents_dir(range_id)
        if target.exists():
            raise ValueError(f"range {range_id} already has documents")
        target.mkdir(parents=True)
        for file in document_files(source):
            shutil.copy2(file, target / file.name)
        for name in sorted(set(bootstrap_names(self._repository.documents(source)))):
            path = user_data_dir(source) / name
            if path.is_file():
                (target / USER_DATA_DIR).mkdir(exist_ok=True)
                shutil.copy2(path, target / USER_DATA_DIR / name)

    def read(self, range_id: UUID) -> tuple[list[Document], dict[str, str]]:
        directory = self._documents(range_id)
        documents = self._repository.documents(directory)
        files: dict[str, str] = {}
        user_data = directory / USER_DATA_DIR
        if user_data.is_dir():
            for path in sorted(user_data.iterdir()):
                if path.is_file():
                    files[path.name] = path.read_text()
        return documents, files

    def replace(
        self, range_id: UUID, documents: Sequence[Document], bootstrap_files: dict[str, str]
    ) -> None:
        """Rewrite the YAML documents and drop user-data files that are no longer named."""
        directory = self._documents(range_id)
        for file in list(directory.iterdir()):
            if file.is_file() and file.suffix in SUFFIXES:
                file.unlink()
        for document in documents:
            content = yaml.safe_dump(
                document.model_dump(mode="json", by_alias=True, exclude_none=True), sort_keys=False
            )
            (directory / _filename(document)).write_text(content)
        target = directory / USER_DATA_DIR
        if target.is_dir():
            for path in list(target.iterdir()):
                if path.is_file() and path.name not in bootstrap_files:
                    path.unlink()
        if bootstrap_files:
            target.mkdir(exist_ok=True)
            for name, text in bootstrap_files.items():
                (target / name).write_text(text)

    def paths(self, range_id: UUID) -> list[Path]:
        directory = self._documents(range_id)
        found = [path for path in directory.iterdir() if path.is_file() and path.suffix in SUFFIXES]
        user_data = directory / USER_DATA_DIR
        if user_data.is_dir():
            found.extend(path for path in user_data.iterdir() if path.is_file())
        return sorted(found)

    def load(self, range_id: UUID, provider: Provider) -> CyberRange:
        directory = self._documents(range_id)
        return dataclasses.replace(self._repository.load(directory, provider), id=range_id)

    def _documents(self, range_id: UUID) -> Path:
        directory = self._home.documents_dir(range_id)
        if not directory.is_dir():
            raise CyberRangeError(f"range {range_id} has no documents in {directory}")
        return directory

    def delete(self, range_id: UUID) -> None:
        directory = self._home.documents_dir(range_id)
        if directory.exists():
            shutil.rmtree(directory)


def _filename(document: Document) -> str:
    kind = {
        "Network": "network",
        "NetworkBinding": "network-binding",
        "Server": "server",
        "ServerBinding": "server-binding",
    }[document.kind]
    return f"{document.metadata.name}.{kind}.yaml"
