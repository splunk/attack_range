# Ansible Role: ([Ludus](https://ludus.cloud)) Attack Range Splunk

An Ansible Role that installs a [Attack Range](https://github.com/splunk/attack_range) Windows Server.

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):
```
ludus_ar_windows_splunk_ip: "10.2.20.1"
ludus_ar_windows_uf_url: "https://download.splunk.com/products/universalforwarder/releases/9.3.0/windows/splunkforwarder-9.3.0-51ccf43db5bd-x64-release.msi"
ludus_ar_windows_password: "changeme123!"
ludus_ar_windows_install_additional_tools: false
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: attack_range_windows
  roles:
    - P4T12ICK.ludus_ar_windows
```

## Example Ludus Range Config

```yaml
ludus:
  - vm_name: "{{ range_id }}-ar-splunk"
    hostname: "{{ range_id }}-ar-splunk"
    template: ubuntu-22.04-x64-server-template
    vlan: 20
    ip_last_octet: 1
    ram_gb: 16
    cpus: 8
    linux: true
    testing:
      snapshot: false
      block_internet: false
    roles:
      - P4T12ICK.ludus_ar_splunk
  - vm_name: "{{ range_id }}-ar-windows"
    hostname: "{{ range_id }}-ar-windows"
    template: win2022-server-x64-template
    vlan: 20
    ip_last_octet: 2
    ram_gb: 8
    cpus: 4
    windows:
      sysprep: false
    roles:
      - P4T12ICK.ludus_ar_windows
    role_vars:
      ludus_ar_windows_splunk_ip: "10.2.20.1"
```

## License
Apache License 2.0

## Author Information
This role was created by [P4T12ICK](https://github.com/P4T12ICK), for [Ludus](https://ludus.cloud/).
