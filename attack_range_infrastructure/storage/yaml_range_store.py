"""RangeStore that keeps each record in `ranges/<id>/range.yaml` of the home folder."""

import os
import tempfile
from uuid import UUID

import yaml
from pydantic import ValidationError

from attack_range.application.range_store import RangeNotFound, RangeStore
from attack_range.domain.entities.range_record import RangeRecord

from .home import AttackRangeHome


class YamlRangeStore(RangeStore):
    def __init__(self, home: AttackRangeHome) -> None:
        self._home = home

    def create(self, record: RangeRecord) -> None:
        if self._home.record_file(record.id).exists():
            raise ValueError(f"range {record.id} already exists")
        self._write(record)

    def get(self, range_id: UUID) -> RangeRecord:
        path = self._home.record_file(range_id)
        if not path.is_file():
            raise RangeNotFound(f"no cyber range with id {range_id}")
        try:
            return RangeRecord.model_validate(yaml.safe_load(path.read_text()))
        except (yaml.YAMLError, ValidationError) as error:
            raise ValueError(f"{path} is not a valid range record: {error}") from error

    def update(self, record: RangeRecord) -> None:
        if not self._home.record_file(record.id).is_file():
            raise RangeNotFound(f"no cyber range with id {record.id}")
        self._write(record)

    def list(self) -> list[RangeRecord]:
        records: list[RangeRecord] = []
        if not self._home.ranges_dir.is_dir():
            return records
        for directory in sorted(self._home.ranges_dir.iterdir()):
            try:
                range_id = UUID(directory.name)
            except ValueError:
                continue
            if self._home.record_file(range_id).is_file():
                try:
                    records.append(self.get(range_id))
                except ValueError:
                    continue
        return records

    def delete(self, range_id: UUID) -> None:
        """Remove the record, and the range folder once nothing else is left in it."""
        path = self._home.record_file(range_id)
        if not path.is_file():
            raise RangeNotFound(f"no cyber range with id {range_id}")
        path.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass

    def _write(self, record: RangeRecord) -> None:
        """Write to a temporary file and rename it, so a reader never sees half a record."""
        path = self._home.record_file(record.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".range-", suffix=".yaml")
        try:
            with os.fdopen(descriptor, "w") as handle:
                handle.write(content)
            os.replace(temporary, path)
        except BaseException:
            os.unlink(temporary)
            raise
