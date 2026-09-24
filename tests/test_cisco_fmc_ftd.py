import logging
import os
import sys
from unittest.mock import MagicMock

import pytest
import yaml

sys.modules.setdefault("ansible_runner", MagicMock())
sys.modules.setdefault("python_vagrant", MagicMock())

from attack_range.managers.ansible_manager import AnsibleManager
from attack_range.managers.config_manager import ConfigManager


CISCO_CONFIG = {
    "general": {
        "cloud_provider": "aws",
        "attack_range_password": "Changeme123!",
    },
    "aws": {
        "private_key_path": "/tmp/id_rsa",
    },
    "attack_range": [
        {
            "name": "fmc",
            "cisco_fmc": True,
            "ip_last_octet": 20,
            "user_name": "admin",
            "become": False,
            "roles": [
                {
                    "role": "P4T12ICK.ar_cisco_fmc",
                    "vars": {
                        "ar_cisco_fmc_ftd_mgmt_ip": "10.0.2.21",
                    },
                }
            ],
        },
        {
            "name": "ftd",
            "cisco_ftd": True,
            "ip_last_octet": 21,
            "user_name": "admin",
        },
    ],
}


def _ar_cisco_fmc_file(*parts):
    role_dir = os.environ.get(
        "AR_CISCO_FMC_ROLE",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ar_cisco_fmc")),
    )
    path = os.path.join(role_dir, *parts)
    if not os.path.exists(path):
        pytest.skip(f"P4T12ICK.ar_cisco_fmc checkout not found at {path}")
    return path


@pytest.fixture
def ansible_manager(tmp_path):
    ansible_dir = tmp_path / "ansible"
    ansible_dir.mkdir()
    (ansible_dir / "roles").mkdir()
    return AnsibleManager(
        ansible_dir=str(ansible_dir),
        inventory_path=str(ansible_dir / "inventory.yaml"),
        config=CISCO_CONFIG,
        cloud_provider="aws",
        logger=logging.getLogger("test"),
    )


class TestCiscoInventoryAndPlaybook:
    def test_inventory_uses_local_connection_for_cisco_hosts(self, ansible_manager):
        ansible_manager.update_inventory_attack_range_servers()
        inventory = yaml.safe_load(open(ansible_manager.inventory_path))

        fmc = inventory["fmc"]["hosts"]["10.0.2.20"]
        assert fmc["ansible_connection"] == "local"
        assert fmc["ansible_user"] == "admin"
        assert fmc["ansible_password"] == "Changeme123!"

        ftd = inventory["ftd"]["hosts"]["10.0.2.21"]
        assert ftd["ansible_connection"] == "local"

    def test_lab_playbook_skips_ftd_and_uses_local_connection_for_fmc(self, ansible_manager):
        ansible_manager.update_lab_playbook()
        plays = yaml.safe_load(open(os.path.join(ansible_manager.ansible_dir, "lab.yaml")))

        hosts = [play["hosts"] for play in plays]
        assert "ftd" not in hosts
        assert "fmc" in hosts

        fmc_play = next(play for play in plays if play["hosts"] == "fmc")
        assert fmc_play["connection"] == "local"
        assert fmc_play["gather_facts"] is False
        assert fmc_play["become"] is False
        assert fmc_play["roles"][0]["role"] == "P4T12ICK.ar_cisco_fmc"

    def test_vpn_allowed_ips_include_ftd_subnets(self, ansible_manager):
        assert ansible_manager._vpn_allowed_ips() == (
            "10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24, 10.0.4.0/24, 10.0.5.0/24"
        )

    def test_vpn_allowed_ips_without_ftd(self, ansible_manager):
        ansible_manager.config = {"attack_range": [{"name": "splunk"}]}
        assert ansible_manager._vpn_allowed_ips() == "10.0.1.0/24, 10.0.2.0/24"

    def test_cisco_template_builds_splunk_then_fmc(self):
        template_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "aws",
            "cisco_fmc_ftd_aws.yml",
        )
        template = yaml.safe_load(open(os.path.abspath(template_path)))
        names = [server["name"] for server in template["attack_range"]]
        assert names == ["splunk", "fmc", "ftd", "win", "kali"]

        splunk_roles = [
            role["role"] if isinstance(role, dict) else role
            for role in template["attack_range"][0]["roles"]
        ]
        assert splunk_roles == [
            "P4T12ICK.ludus_ar_splunk",
            "P4T12ICK.ar_guacamole",
        ]
        kali = template["attack_range"][4]
        assert kali["ami_name_filter"] == "debian-kali-last-snapshot-amd64-*"
        assert kali["ami_product_code"] == "7lgvy7mt78lgoi4lant0znp5h"
        fmc_vars = template["attack_range"][1]["roles"][0]["vars"]
        splunk_vars = template["attack_range"][0]["roles"][0]["vars"]
        assert splunk_vars["ludus_ar_splunk_syslog"] is True
        assert "cisco-security-cloud_372.tgz" in splunk_vars["ludus_ar_splunk_apps"]
        assert template["attack_range"][1]["roles"][0]["role"] == "P4T12ICK.ar_cisco_fmc"
        assert fmc_vars["ar_cisco_fmc_syslog_host"] == "10.0.2.10"
        assert fmc_vars["ar_cisco_fmc_syslog_port"] == 514
        assert fmc_vars["ar_cisco_fmc_splunk_port"] == 1514
        assert fmc_vars["ar_cisco_fmc_ftd_performance_tier"] == "FTDv5"
        assert fmc_vars["ar_cisco_fmc_ftd_outside_ip"] == "10.0.4.21"
        assert fmc_vars["ar_cisco_fmc_ftd_inside_ip"] == "10.0.5.21"

        win = template["attack_range"][3]
        assert win["windows"] is True
        assert win["network"] == "inside"
        assert win["ip_last_octet"] == 11
        assert win["roles"][0]["role"] == "P4T12ICK.ludus_ar_windows"

    def test_lab_playbook_runs_splunk_before_fmc(self, ansible_manager):
        ansible_manager.config = {
            "general": CISCO_CONFIG["general"],
            "aws": CISCO_CONFIG["aws"],
            "attack_range": [
                {
                    "name": "splunk",
                    "linux": True,
                    "ip_last_octet": 10,
                    "user_name": "ubuntu",
                    "roles": [
                        {"role": "P4T12ICK.ludus_ar_splunk", "vars": {"ludus_ar_splunk_syslog": True}},
                    ],
                },
                *CISCO_CONFIG["attack_range"],
                {
                    "name": "win",
                    "windows": True,
                    "network": "inside",
                    "ip_last_octet": 11,
                    "user_name": "Administrator",
                    "roles": [{"role": "P4T12ICK.ludus_ar_windows"}],
                },
            ],
        }
        ansible_manager.update_lab_playbook()
        plays = yaml.safe_load(open(os.path.join(ansible_manager.ansible_dir, "lab.yaml")))
        hosts = [play["hosts"] for play in plays]
        assert hosts == ["splunk", "fmc", "win"]
        assert "become" not in plays[2]
        assert plays[2]["pre_tasks"][0]["name"] == "Wait for WinRM"
        assert len(plays[2]["pre_tasks"]) == 1
        ansible_manager.update_inventory_attack_range_servers()
        inventory = yaml.safe_load(open(ansible_manager.inventory_path))
        win = inventory["win"]["hosts"]["10.0.5.11"]
        assert win["ansible_connection"] == "winrm"
        assert [role["role"] for role in plays[0]["roles"]] == [
            "P4T12ICK.ludus_ar_splunk",
        ]

    def test_fmc_role_configures_audit_syslog(self):
        tasks = yaml.safe_load(open(_ar_cisco_fmc_file("tasks", "main.yml")))
        names = [task.get("name") for task in tasks]
        assert "Configure FMC audit log export to syslog" in names
        assert "Configure Integrations/Splunk event export after FTD registration" in names
        assert "Wait for FTD SSH (first boot can take 30-45 minutes)" in names
        assert "Wait until FTD appears in FMC" in names
        assert "Start FMC 90-day evaluation license" in names
        assert "Wait for FTD registration task" in names
        assert "Configure FTD for first policy deploy" in names
        assert "Configure FTD inspection policy for inside hosts" in names
        assert "Deploy FTD policy" in names

        register = next(task for task in tasks if task.get("name") == "Register FTD with FMC")
        body = register["ansible.builtin.uri"]["body"]
        assert body["performanceTier"] == "{{ ar_cisco_fmc_ftd_performance_tier }}"
        assert "license_caps" in body

        defaults = open(_ar_cisco_fmc_file("defaults", "main.yml")).read()
        assert "ar_cisco_fmc_ftd_performance_tier: FTDv5" in defaults
        assert "systemconfiguration/auditlog" in defaults
        first_deploy = open(_ar_cisco_fmc_file("tasks", "ftd_first_deploy.yml")).read()
        assert "Name and enable FTD data interfaces" in first_deploy
        assert "Ethernet0/0" in first_deploy
        assert "enableSplunk" in first_deploy
        deploy = open(_ar_cisco_fmc_file("tasks", "ftd_deploy.yml")).read()
        assert "Resolve FTD deploy version" in deploy
        assert "Wait for FTD policy deploy" in deploy
        assert "include_tasks: ftd_deploy_poll.yml" in deploy
        assert "ar_cisco_fmc_deploy_poll_i" in deploy
        assert "Fail if FTD policy deploy did not finish" in deploy
        poll = open(_ar_cisco_fmc_file("tasks", "ftd_deploy_poll.yml")).read()
        assert "Refresh FMC API session after deploy-wait 401" in poll
        assert "status_code: [200, 401]" in poll
        assert "Pause between FTD deploy status polls" in poll
        assert "ar_cisco_fmc_deploy_success_statuses" in poll
        assert "succeeded" in poll
        assert "ar_cisco_fmc_deploy_task_poll" in poll
        assert "ar_cisco_fmc_deploy_task_retry" in poll
        assert "Keep the successful FTD deploy status response" in poll
        inspection = open(_ar_cisco_fmc_file("tasks", "ftd_inspection.yml")).read()
        assert "Allow and log inspected traffic" in inspection
        assert "ipsPolicy" in inspection
        assert "intrusionpolicies" in inspection
        assert "Create lab IPS policy and enable the testmyids signature" in inspection
        assert "Attach intrusion policy to existing allow-inspect rule" in inspection
        assert "Resolve existing allow-inspect rule ID" in inspection
        assert "ar_cisco_fmc_intrusion_policy_name: Balanced Security and Connectivity" in defaults
        assert "ar_cisco_fmc_lab_ips_policy_name: AR-IPS-Policy" in defaults
        assert "ar_cisco_fmc_test_ips_sid: 498" in defaults
        ips = open(_ar_cisco_fmc_file("tasks", "ftd_ips.yml")).read()
        assert "overrideState: ALERT" in ips
        assert "object/intrusionrules" in ips
        nat = open(_ar_cisco_fmc_file("tasks", "ftd_nat.yml")).read()
        assert "interfaceInTranslatedNetwork" in nat
        assert "assignment/policyassignments" in nat
        assert "FTDAutoNatRule" in nat
        assert "translatedNetworkIsDestinationInterface" not in nat
        assert "include_tasks: ftd_nat.yml" in open(_ar_cisco_fmc_file("tasks", "main.yml")).read()
        assert "AR-Inside" in defaults
        assert "ar_cisco_fmc_deploy_success_statuses" in defaults
        audit = open(_ar_cisco_fmc_file("tasks", "audit_syslog.yml")).read()
        assert "policy/syslogalerts" not in audit
        profile = open(_ar_cisco_fmc_file("tasks", "splunk_profile.yml")).read()
        assert "type: Host" in profile
        assert "eventTypes" in profile
        assert "destination:" in profile
        assert "eventSelection:" in profile
        assert "sourceSelection:" in profile
        assert "sendEventsUsingManagementInterface: true" in profile

    def test_aws_network_steers_inside_hosts_through_ftd(self):
        aws_tf = open(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "terraform",
                    "aws",
                    "resources.tf",
                )
            )
        ).read()
        assert "aws_route_table" in aws_tf
        assert "cisco_inside" in aws_tf
        assert "aws_eip" in aws_tf
        assert "cisco_ftd_outside" in aws_tf
        assert "public_route_table_ids" in open(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "terraform",
                    "aws",
                    "modules",
                    "network",
                    "resources.tf",
                )
            )
        ).read()
        assert 'try(each.value.network, "mgmt")' in aws_tf

    def test_galaxy_role_is_installed(self, ansible_manager, monkeypatch):
        ansible_manager.config = {
            "general": CISCO_CONFIG["general"],
            "attack_range": [
                *CISCO_CONFIG["attack_range"],
            ],
        }

        called = []

        def fake_install(role_name, force=True, max_retries=3):
            called.append(role_name)
            return True

        monkeypatch.setattr(ansible_manager, "install_ansible_galaxy_role", fake_install)
        ansible_manager.update_ansible_galaxy_roles()
        assert called == ["P4T12ICK.ar_cisco_fmc"]


class TestCiscoConfigValidation:
    def test_rejects_cisco_on_azure(self, tmp_path):
        logger = logging.getLogger("test")
        config = {
            "general": {"cloud_provider": "azure", "attack_range_password": "Changeme123!"},
            "attack_range": [{"name": "fmc", "cisco_fmc": True}],
        }
        manager = ConfigManager(config, str(tmp_path / "c.yml"), str(tmp_path), logger)
        with pytest.raises(SystemExit):
            manager.validate_cisco_aws_only()

    def test_allows_cisco_on_aws(self, tmp_path):
        logger = logging.getLogger("test")
        config = {
            "general": {"cloud_provider": "aws", "attack_range_password": "Changeme123!"},
            "attack_range": [{"name": "fmc", "cisco_fmc": True}],
        }
        manager = ConfigManager(config, str(tmp_path / "c.yml"), str(tmp_path), logger)
        manager.validate_cisco_aws_only()


class TestServerPrivateIp:
    def test_default_and_inside_networks(self):
        from attack_range.utils import server_private_ip

        assert server_private_ip({"ip_last_octet": 10}) == "10.0.2.10"
        assert server_private_ip({"ip_last_octet": 11, "network": "inside"}) == "10.0.5.11"
        assert server_private_ip({"ip_last_octet": 21, "network": "outside"}) == "10.0.4.21"
