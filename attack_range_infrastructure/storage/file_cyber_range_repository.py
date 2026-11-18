"""Reads a cyber range from YAML documents and the `user-data/` folder next to them."""

from pathlib import Path
from typing import Optional

import yaml

from attack_range.application.cyber_range import CyberRange, CyberRangeError, Document, assemble_cyber_range
from attack_range.application.repository import CyberRangeRepository
from attack_range.domain.entities import Server, parse_document
from attack_range.domain.entities.common import Provider

USER_DATA_DIR = "user-data"
SUFFIXES = (".yaml", ".yml")


def document_files(location: Path) -> list[Path]:
    """The YAML files of a template: the file itself, or every `*.yaml` and `*.yml` directly in the directory."""
    location = Path(location)
    if location.is_file():
        return [location]
    if location.is_dir():
        return sorted(path for path in location.iterdir() if path.is_file() and path.suffix in SUFFIXES)
    raise CyberRangeError(f"{location} is neither a file nor a directory")


def user_data_dir(location: Path) -> Path:
    """Where the bootstrap files of a template live."""
    location = Path(location)
    return (location.parent if location.is_file() else location) / USER_DATA_DIR


def bootstrap_names(documents: list[Document]) -> list[str]:
    return [
        document.spec.bootstrap.user_data
        for document in documents
        if isinstance(document, Server) and document.spec.bootstrap is not None
    ]


class FileCyberRangeRepository(CyberRangeRepository):
    """Each YAML file holds one or more documents, separated by `---`."""

    def load(self, location: Path, provider: Optional[Provider] = None) -> CyberRange:
        documents = self.documents(location)
        files: dict[str, str] = {}
        for name in bootstrap_names(documents):
            path = user_data_dir(location) / name
            if path.is_file():
                files[name] = path.read_text()
        try:
            return assemble_cyber_range(documents, provider, files)
        except CyberRangeError as error:
            raise CyberRangeError(f"{location}: {error}") from error

    @staticmethod
    def documents(location: Path) -> list[Document]:
        documents: list[Document] = []
        for file in document_files(location):
            try:
                loaded = list(yaml.safe_load_all(file.read_text()))
            except yaml.YAMLError as error:
                raise CyberRangeError(f"{file.name}: {error}") from error
            for data in loaded:
                if data is None:
                    continue
                try:
                    documents.append(parse_document(data))
                except ValueError as error:
                    raise CyberRangeError(f"{file.name}: {error}") from error
        return documents
