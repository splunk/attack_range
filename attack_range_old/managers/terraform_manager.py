"""
Terraform manager for Attack Range.

This module handles Terraform operations including initialization, apply, destroy,
and output retrieval.
"""

import os
import sys
import json
import subprocess
import shutil
import logging
from python_terraform import Terraform, IsNotFlagged


class TerraformManager:
    """Manages Terraform operations."""

    def __init__(self, terraform_dir: str, config: dict, logger: logging.Logger):
        """
        Initialize the Terraform manager.

        :param terraform_dir: Directory containing Terraform configuration
        :param config: Configuration dictionary
        :param logger: Logger instance
        """
        self.terraform_dir = terraform_dir
        self.config = config
        self.logger = logger
        
        # Determine cloud provider and prepare variables
        cloud_provider = config.get("general", {}).get("cloud_provider", "aws").lower()
        
        if cloud_provider == "azure":
            terraform_vars = {
                "general": config.get("general", {}),
                "azure": config.get("azure", {}),
                "attack_range": config.get("attack_range", []),
            }
        elif cloud_provider == "gcp":
            terraform_vars = {
                "general": config.get("general", {}),
                "gcp": config.get("gcp", {}),
                "attack_range": config.get("attack_range", []),
            }
        else:  # aws
            terraform_vars = {
                "general": config.get("general", {}),
                "aws": config.get("aws", {}),
                "attack_range": config.get("attack_range", []),
            }
        
        # Initialize terraform
        self.terraform = Terraform(
            working_dir=terraform_dir,
            variables=terraform_vars,
            parallelism=15,
        )

    def update_variables(self) -> None:
        """
        Update terraform variables with current config.
        This is needed after generating attack_range_id or updating config.
        """
        cloud_provider = self.config.get("general", {}).get("cloud_provider", "aws").lower()
        
        if cloud_provider == "azure":
            terraform_vars = {
                "general": self.config.get("general", {}),
                "azure": self.config.get("azure", {}),
                "attack_range": self.config.get("attack_range", []),
            }
        elif cloud_provider == "gcp":
            terraform_vars = {
                "general": self.config.get("general", {}),
                "gcp": self.config.get("gcp", {}),
                "attack_range": self.config.get("attack_range", []),
            }
        else:  # aws
            terraform_vars = {
                "general": self.config.get("general", {}),
                "aws": self.config.get("aws", {}),
                "attack_range": self.config.get("attack_range", []),
            }
        
        self.terraform.variables = terraform_vars

    def init(self, backend_was_created: bool = False) -> None:
        """
        Initialize Terraform.

        :param backend_was_created: If True, use -reconfigure, otherwise use -migrate-state
        """
        cwd = os.getcwd()
        try:
            os.chdir(self.terraform_dir)
            
            # Clean up .terraform directory if it exists to avoid stale backend configs
            terraform_dir_path = os.path.join(self.terraform_dir, ".terraform")
            if os.path.exists(terraform_dir_path):
                self.logger.info("Cleaning up existing .terraform directory to avoid stale backend configs...")
                shutil.rmtree(terraform_dir_path)
            
            # Use -reconfigure for fresh setups, -migrate-state if backend already existed.
            # -upgrade allows provider version bumps when lock file is older than module constraints.
            init_flags = (
                ["-reconfigure", "-input=false", "-upgrade"]
                if backend_was_created
                else ["-migrate-state", "-input=false", "-upgrade"]
            )
            init_result = subprocess.run(
                ["terraform", "init"] + init_flags,
                capture_output=True,
                text=True
            )
            if init_result.returncode != 0:
                msg = init_result.stderr or init_result.stdout or "Terraform init failed"
                self.logger.error(f"Terraform init failed: {msg}")
                raise RuntimeError(msg)
            self.logger.info("Terraform initialized successfully")
        finally:
            os.chdir(cwd)

    def init_for_destroy(self) -> None:
        """
        Initialize Terraform for destroy operation.
        Uses -reconfigure to avoid interactive prompts.
        """
        cwd = os.getcwd()
        try:
            os.chdir(self.terraform_dir)
            init_result = subprocess.run(
                ["terraform", "init", "-reconfigure", "-input=false", "-upgrade"],
                capture_output=True,
                text=True
            )
            if init_result.returncode != 0:
                msg = init_result.stderr or init_result.stdout or "Terraform init failed"
                self.logger.error(f"Terraform init failed: {msg}")
                raise RuntimeError(msg)
            self.logger.info("Terraform initialized successfully")
        finally:
            os.chdir(cwd)

    def apply(self) -> None:
        """
        Apply Terraform configuration.
        """
        self.logger.info("Applying terraform configuration...")
        return_code, stdout, stderr = self.terraform.apply(
            capture_output="yes", skip_plan=True, no_color=IsNotFlagged
        )

        if return_code != 0:
            self.logger.error("Terraform apply failed!")
            if stderr:
                self.logger.error(f"Terraform stderr:\n{stderr}")
            if stdout:
                self.logger.error(f"Terraform stdout:\n{stdout}")
            if not stderr and not stdout:
                self.logger.error("No error output from terraform (return code != 0)")
            raise RuntimeError(stderr or stdout or "Terraform apply failed")
        self.logger.info("Terraform apply completed successfully")

    def force_unlock(self, lock_id: str) -> None:
        """
        Force unlock Terraform state.
        
        :param lock_id: Lock ID to unlock (from terraform error message)
        """
        self.logger.info(f"Force unlocking terraform state with lock ID: {lock_id}")
        cwd = os.getcwd()
        try:
            os.chdir(self.terraform_dir)
            unlock_result = subprocess.run(
                ["terraform", "force-unlock", "-force", lock_id],
                capture_output=True,
                text=True
            )
            if unlock_result.returncode != 0:
                self.logger.warning(f"Terraform force-unlock failed: {unlock_result.stderr}")
                # Don't raise - this is best effort
            else:
                self.logger.info("Terraform state unlocked successfully")
        finally:
            os.chdir(cwd)

    def destroy(self) -> None:
        """
        Destroy Terraform infrastructure.
        Attempts to unlock state if locked.
        """
        self.logger.info("Destroying terraform infrastructure...")
        return_code, stdout, stderr = self.terraform.destroy(
            capture_output="yes",
            no_color=IsNotFlagged,
            force=IsNotFlagged,
            auto_approve=True,
        )

        if return_code != 0:
            # Check if error is due to locked state
            error_output = stderr or stdout or ""
            if "Error acquiring the state lock" in error_output or "lock is currently held" in error_output.lower():
                # Try to extract lock ID from error message
                import re
                lock_id_match = re.search(r'Lock ID:\s*([a-f0-9-]+)', error_output, re.IGNORECASE)
                if lock_id_match:
                    lock_id = lock_id_match.group(1)
                    self.logger.warning(f"Terraform state is locked. Attempting to unlock with ID: {lock_id}")
                    self.force_unlock(lock_id)
                    # Retry destroy after unlock
                    self.logger.info("Retrying terraform destroy after unlock...")
                    return_code, stdout, stderr = self.terraform.destroy(
                        capture_output="yes",
                        no_color=IsNotFlagged,
                        force=IsNotFlagged,
                        auto_approve=True,
                    )
            
            if return_code != 0:
                self.logger.error(f"Terraform destroy failed: {stderr}")
                raise RuntimeError(stderr or "Terraform destroy failed")
        self.logger.info("Terraform infrastructure destroyed successfully")

    def get_output(self, output_name: str) -> str:
        """
        Get a terraform output value.

        :param output_name: Name of the terraform output
        :return: Output value as string or None if not found
        """
        cwd = os.getcwd()
        try:
            os.chdir(self.terraform_dir)

            # First, check if the output exists
            list_result = subprocess.run(
                ["terraform", "output", "-json"],
                capture_output=True,
                text=True
            )

            if list_result.returncode == 0:
                outputs = json.loads(list_result.stdout)
                if output_name not in outputs:
                    available_outputs = list(outputs.keys())
                    self.logger.error(
                        f"Terraform output '{output_name}' not found. "
                        f"Available outputs: {', '.join(available_outputs) if available_outputs else 'none'}"
                    )
                    return None

            # Get the output value
            result = subprocess.run(
                ["terraform", "output", "-raw", output_name],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.logger.error(
                    f"Failed to get terraform output '{output_name}': {result.stderr}\n"
                    f"stdout: {result.stdout}"
                )
                # Try to list all outputs for debugging
                list_all = subprocess.run(
                    ["terraform", "output"],
                    capture_output=True,
                    text=True
                )
                if list_all.returncode == 0:
                    self.logger.info(f"Available terraform outputs:\n{list_all.stdout}")
                return None

            output_value = result.stdout.strip()
            return output_value

        finally:
            os.chdir(cwd)
