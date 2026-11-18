"""Terraform provisioner: renders `main.tf.json` and drives the terraform CLI."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from attack_range.application.cyber_range import CyberRange
from attack_range.application.provisioner import ProvisionLog, ProvisionResult, Provisioner, ProvisionerError
from attack_range.domain.entities.common import Provider
from attack_range_infrastructure.storage.home import AttackRangeHome

from .backends import AzureBlobBackend, LocalBackend, S3Backend, TerraformBackend
from .renderers.aws import AwsRenderer
from .renderers.azure import AzureRenderer
from .renderers.base import RenderError, Renderer
from .renderers.vmware import VmwareRenderer

CONFIG_FILE = "main.tf.json"
PLAN_FILE = "tfplan"


class TerraformProvisioner(Provisioner):
    """Provisions a cyber range with Terraform.

    The code of a registered range goes to `ranges/<id>/terraform/` in the home folder. State
    lives in S3 for AWS, in Azure Blob Storage for Azure, and next to the code for VMware,
    unless `backends` says otherwise. Existing local state is copied into a new backend on
    the next init. A range without an id is planned in `plans/<name>-<provider>/` with local
    state and cannot be applied. Credentials come from the usual environment variables
    (AWS_*, ARM_*, VSPHERE_*).
    """

    def __init__(
        self,
        home: AttackRangeHome,
        terraform_bin: str = "terraform",
        renderers: Optional[dict[Provider, Renderer]] = None,
        backends: Optional[dict[Provider, TerraformBackend]] = None,
        log: Optional[ProvisionLog] = None,
    ) -> None:
        super().__init__(log)
        self.home = home
        self.terraform_bin = terraform_bin
        self.renderers: dict[Provider, Renderer] = renderers or {
            "aws": AwsRenderer(),
            "azure": AzureRenderer(),
            "vmware": VmwareRenderer(),
        }
        self.backends: dict[Provider, TerraformBackend] = backends or {
            "aws": S3Backend(),
            "azure": AzureBlobBackend(),
            "vmware": LocalBackend(),
        }

    def directory(self, cyber_range: CyberRange) -> Path:
        """Directory that holds the generated code of this cyber range."""
        if cyber_range.id is None:
            return self.home.plan_dir(cyber_range.name, cyber_range.provider)
        return self.home.terraform_dir(cyber_range.id)

    def backend(self, cyber_range: CyberRange) -> TerraformBackend:
        if cyber_range.id is None or cyber_range.local_state:
            return LocalBackend()
        return self.backends.get(cyber_range.provider) or LocalBackend()

    def render(self, cyber_range: CyberRange) -> Path:
        renderer = self.renderers.get(cyber_range.provider)
        if renderer is None:
            raise ProvisionerError(f"no Terraform renderer for provider '{cyber_range.provider}'")
        try:
            document = renderer.render(cyber_range)
        except RenderError as error:
            raise ProvisionerError(str(error)) from error
        backend = self.backend(cyber_range)
        if backend.type is not None:
            document["terraform"]["backend"] = {backend.type: {}}
        content = json.dumps(document, indent=2) + "\n"

        directory = self.directory(cyber_range)
        directory.mkdir(parents=True, exist_ok=True)
        config = directory / CONFIG_FILE
        if not config.is_file() or config.read_text() != content:
            config.write_text(content)
            (directory / PLAN_FILE).unlink(missing_ok=True)
        return directory

    def plan(self, cyber_range: CyberRange) -> ProvisionResult:
        directory = self.render(cyber_range)
        return self._run_all(cyber_range, directory, ["plan", "-input=false", "-no-color", f"-out={PLAN_FILE}"])

    def apply(self, cyber_range: CyberRange) -> ProvisionResult:
        self._require_id(cyber_range, "applied")
        directory = self.render(cyber_range)
        plan_file = directory / PLAN_FILE
        args = ["apply", "-input=false", "-no-color", "-auto-approve"]
        if plan_file.is_file():
            args.append(PLAN_FILE)
        result = self._run_all(cyber_range, directory, args)
        plan_file.unlink(missing_ok=True)
        if not result.success:
            return result
        return ProvisionResult(success=True, output=result.output, outputs=self._outputs(directory))

    def destroy(self, cyber_range: CyberRange) -> ProvisionResult:
        self._require_id(cyber_range, "destroyed")
        directory = self.render(cyber_range)
        result = self._run_all(cyber_range, directory, ["destroy", "-input=false", "-no-color", "-auto-approve"])
        (directory / PLAN_FILE).unlink(missing_ok=True)
        return result

    def clean(self, cyber_range: CyberRange) -> None:
        self._require_id(cyber_range, "cleaned")
        shutil.rmtree(self.directory(cyber_range), ignore_errors=True)

    @staticmethod
    def _require_id(cyber_range: CyberRange, verb: str) -> None:
        if cyber_range.id is None:
            raise ProvisionerError(f"cyber range '{cyber_range.name}' has no id; only registered ranges can be {verb}")

    def _init_args(self, cyber_range: CyberRange) -> list[str]:
        """Prepare the state backend and return the `terraform init` arguments for it."""
        backend = self.backend(cyber_range)
        try:
            backend.ensure(cyber_range)
            settings = backend.config(cyber_range)
        except Exception as error:
            raise ProvisionerError(f"could not prepare the {backend.type or 'local'} state backend: {error}") from error
        args = ["init", "-input=false", "-no-color"]
        if settings:
            args += ["-migrate-state", "-force-copy"]
            args += [f"-backend-config={key}={value}" for key, value in settings.items()]
        return args

    def _run_all(self, cyber_range: CyberRange, directory: Path, args: list[str]) -> ProvisionResult:
        """Run `terraform init`, then the given command, stopping at the first failure."""
        output: list[str] = []
        for command in (self._init_args(cyber_range), args):
            completed = self._run(command, directory)
            output.append(completed.stdout + completed.stderr)
            if completed.returncode != 0:
                return ProvisionResult(success=False, output="".join(output))
        return ProvisionResult(success=True, output="".join(output))

    def _outputs(self, directory: Path) -> dict[str, Any]:
        completed = self._run(["output", "-json"], directory, stream=False)
        if completed.returncode != 0:
            raise ProvisionerError(f"terraform output failed: {completed.stderr}")
        return {name: entry["value"] for name, entry in json.loads(completed.stdout or "{}").items()}

    def _run(self, args: list[str], directory: Path, stream: bool = True) -> subprocess.CompletedProcess[str]:
        """Run terraform. A streamed run sends each line to the log and merges stderr into stdout."""
        command = [self.terraform_bin, *args]
        try:
            if not stream:
                return subprocess.run(command, cwd=directory, capture_output=True, text=True, check=False)
            lines: list[str] = []
            with subprocess.Popen(
                command, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            ) as process:
                assert process.stdout is not None
                for line in process.stdout:
                    lines.append(line)
                    self.log.line(line.rstrip("\n"))
            return subprocess.CompletedProcess(command, process.returncode, "".join(lines), "")
        except FileNotFoundError as error:
            raise ProvisionerError(f"terraform binary '{self.terraform_bin}' not found") from error
