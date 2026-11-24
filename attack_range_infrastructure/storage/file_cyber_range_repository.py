"""Reads a cyber range from YAML documents and the `user-data/` folder next to them.

A server with no `bootstrap.userData` uses `config/user_data/<server>.<provider>.*` when
that file exists. A set name such as `win.ps1` uses `config/user_data/win.<provider>.ps1`
when that file exists. Other names are read from the template's `user-data/` folder.
"""

from pathlib import Path
from typing import Optional

import yaml

from attack_range.application.cyber_range import CyberRange, CyberRangeError, Document, assemble_cyber_range
from attack_range.application.repository import CyberRangeRepository
from attack_range.domain.entities import NetworkBinding, Server, parse_document
from attack_range.domain.entities.server import Bootstrap
from attack_range.domain.entities.common import Provider

from .home import AttackRangeHome
from .tokens import contains_token, substitute
from .user_config import UserConfig

USER_DATA_DIR = "user-data"
SUFFIXES = (".yaml", ".yml")
BUILTIN_USER_DATA = Path(__file__).resolve().parents[1] / "config" / "user_data"


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


def builtin_user_data(name: str, provider: Provider) -> Optional[str]:
    """Contents of `config/user_data/<stem>.<provider><suffix>`, when that file exists."""
    path = Path(name)
    candidate = BUILTIN_USER_DATA / f"{path.stem}.{provider}{path.suffix}"
    if candidate.is_file():
        return candidate.read_text()
    return None


def _default_builtin(server_name: str, provider: Provider) -> Optional[tuple[str, str]]:
    """`(logical name, contents)` of `config/user_data/<server>.<provider>.*`."""
    matches = sorted(path for path in BUILTIN_USER_DATA.glob(f"{server_name}.{provider}.*") if path.is_file())
    if not matches:
        return None
    if len(matches) > 1:
        found = ", ".join(path.name for path in matches)
        raise CyberRangeError(f"server '{server_name}' matches more than one {provider} user data file: {found}")
    path = matches[0]
    return f"{server_name}{path.suffix}", path.read_text()


def _single_provider(documents: list[Document]) -> Optional[Provider]:
    providers = {document.spec.provider for document in documents if isinstance(document, NetworkBinding)}
    if len(providers) == 1:
        return providers.pop()
    return None


def _with_builtin_user_data(
    documents: list[Document], files: dict[str, str], provider: Optional[Provider]
) -> tuple[list[Document], dict[str, str]]:
    if provider is None:
        return documents, files
    resolved_files = dict(files)
    resolved_documents: list[Document] = []
    for document in documents:
        if isinstance(document, Server) and document.spec.bootstrap is None:
            found = _default_builtin(document.metadata.name, provider)
            if found is not None:
                name, text = found
                resolved_files[name] = text
                document = document.model_copy(
                    update={"spec": document.spec.model_copy(update={"bootstrap": Bootstrap(user_data=name)})}
                )
        resolved_documents.append(document)
    for name in bootstrap_names(resolved_documents):
        builtin = builtin_user_data(name, provider)
        if builtin is not None:
            resolved_files[name] = builtin
    return resolved_documents, resolved_files


def bootstrap_names(documents: list[Document]) -> list[str]:
    return [
        document.spec.bootstrap.user_data
        for document in documents
        if isinstance(document, Server) and document.spec.bootstrap is not None
    ]


class FileCyberRangeRepository(CyberRangeRepository):
    """Each YAML file holds one or more documents, separated by `---`.

    `load` replaces `$USER$` and `$PASSWORD$` with the user name and password from
    the home config. `read` leaves the tokens in place, so a stored template keeps them.
    """

    def __init__(self, home: Optional[AttackRangeHome] = None) -> None:
        self._home = home

    def load(self, location: Path, provider: Optional[Provider] = None) -> CyberRange:
        documents, files = self.read(location)
        documents, files = _with_builtin_user_data(documents, files, provider or _single_provider(documents))
        try:
            documents, files = self._resolve(documents, files)
            return assemble_cyber_range(documents, provider, files)
        except CyberRangeError as error:
            raise CyberRangeError(f"{location}: {error}") from error

    def read(self, location: Path) -> tuple[list[Document], dict[str, str]]:
        documents = self.documents(location)
        if not documents:
            raise CyberRangeError(f"{location} has no documents")
        files: dict[str, str] = {}
        for name in bootstrap_names(documents):
            path = user_data_dir(location) / name
            if path.is_file():
                files[name] = path.read_text()
        return documents, files

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

    def _resolve(
        self, documents: list[Document], files: dict[str, str]
    ) -> tuple[list[Document], dict[str, str]]:
        """Fill `$USER$` and `$PASSWORD$` from the home config when this repository has one."""
        if self._home is None:
            return documents, files
        config = UserConfig.load(self._home)
        dumped = [document.model_dump(mode="json", by_alias=True, exclude_none=True) for document in documents]
        if config is None:
            if any(contains_token(data) for data in dumped) or any(
                contains_token(name) or contains_token(text) for name, text in files.items()
            ):
                raise CyberRangeError(
                    f"{self._home.config_file} has no user name and password "
                    "to replace $USER$ and $PASSWORD$"
                )
            return documents, files
        tokens = {"$USER$": config.user_name, "$PASSWORD$": config.password}
        try:
            resolved = [parse_document(substitute(data, tokens)) for data in dumped]
        except ValueError as error:
            raise CyberRangeError(str(error)) from error
        resolved_files = {
            substitute(name, tokens): substitute(text, tokens) for name, text in files.items()
        }
        return resolved, resolved_files
