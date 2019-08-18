# Splunk Attack Range

## Purpose
This lab has been designed with reproducability in mind. Its primary purpose is to allow the user to quickly build a Windows vm that comes pre-loaded with.

* Splunk Universal Forwarder
* AttackIQ Firedrill
* Sysmon
* Splunk Stream Forwarder

It can easily be modified to fit most needs or expanded to include additional hosts.

NOTE: This lab has not been hardened in any way and runs with default vagrant credentials. Please do not connect or bridge it to any networks you care about. 
---

## Requirements
* [Virtual Box v6.0](https://www.virtualbox.org/wiki/Downloads)
* [Vagrant v2.2.4](https://www.vagrantup.com/downloads.html)
* [Packer v1.3.4](https://www.packer.io/intro/getting-started/install.html)
* [Ansible v2.7.8](https://pypi.org/project/ansible/)
* pywinrm > 0.2.2 `pip install "pywinrm>=0.2.2"`		

## Quickstart
Splunk Attack Range now contains build scripts for Windows client machines!

## Building The Environment

[How to build the environement](docs/Build.md)

## Bringing Up the Environment
[How to start the environement](docs/Starting.md)

## Known Issues and Workarounds

**Issue:** Ansible on OSX crashes with: 
`
objc[22402]: +[__NSPlaceholderDate initialize] may have been in progress in another thread when fork() was called.
objc[22402]: +[__NSPlaceholderDate initialize] may have been in progress in another thread when fork() was called. We cannot safely call it or ignore it in the fork() child process. Crashing instead. Set a breakpoint on objc_initializeAfterForkError to debug.
`
**Workaround:** In the same shell type: `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`

