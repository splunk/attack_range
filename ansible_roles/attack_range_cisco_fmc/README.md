# Ansible Role: Attack Range Cisco FMC

An Ansible role that waits for Cisco Secure Firewall Management Center (FMCv), registers FTDv, deploys lab access/NAT/IPS policy, and optionally exports events to Splunk. Used by [Attack Range](https://github.com/splunk/attack_range) and [Ludus](https://ludus.cloud).

The role uses a **local** connection to call the FMC REST API. Inventory `ansible_password` is used when `ar_cisco_fmc_password` is not set.

## Role Variables

See `defaults/main.yml`. Common overrides:

```
ar_cisco_fmc_password: changeme123!
ar_cisco_fmc_ftd_name: ftd
ar_cisco_fmc_ftd_mgmt_ip: 10.0.2.21
ar_cisco_fmc_reg_key: cisco
ar_cisco_fmc_nat_id: cisco
ar_cisco_fmc_ftd_performance_tier: FTDv5
ar_cisco_fmc_ftd_outside_ip: 10.0.4.21
ar_cisco_fmc_ftd_inside_ip: 10.0.5.21
ar_cisco_fmc_syslog_host: 10.0.2.10
ar_cisco_fmc_syslog_port: 514
ar_cisco_fmc_splunk_port: 1514
```

Leave `ar_cisco_fmc_ftd_mgmt_ip` empty to configure FMC only (no FTD registration). Set `ar_cisco_fmc_syslog_host` to enable audit syslog probes and the Integrations/Splunk profile.

## Example Playbook

```yaml
- hosts: fmc
  connection: local
  gather_facts: false
  become: false
  roles:
    - role: P4T12ICK.ar_cisco_fmc
      vars:
        ar_cisco_fmc_password: changeme123!
        ar_cisco_fmc_ftd_mgmt_ip: 10.0.2.21
        ar_cisco_fmc_syslog_host: 10.0.2.10
```

## License
GNU General Public License v3.0

## Author Information
This role was created by [P4T12ICK](https://github.com/P4T12ICK), for [Ludus](https://ludus.cloud/) and Attack Range.
