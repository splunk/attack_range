"""RangeDocuments that copies a template into `ranges/<id>/documents/` of the home folder."""

import dataclasses
import shutil
from pathlib import Path
from uuid import UUID

from attack_range.application.cyber_range import CyberRange, CyberRangeError
from attack_range.application.range_documents import RangeDocuments
from attack_range.domain.entities.common import Provider

from .file_cyber_range_repository import (
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

    def load(self, range_id: UUID, provider: Provider) -> CyberRange:
        directory = self._home.documents_dir(range_id)
        if not directory.is_dir():
            raise CyberRangeError(f"range {range_id} has no documents in {directory}")
        return dataclasses.replace(self._repository.load(directory, provider), id=range_id)
