Role Name
========

Install a Phantom server from RPMs on CentOS/RHEL 7

Requirements
------------

Obtain the ansible-vault password file and put it in ~/.attack_vault_pass.txt, then run `export ANSIBLE_VAULT_PASSWORD_FILE=~/.attack_vault_pass.txt` to direct ansible-vault to that file.

Role Variables
--------------

The following variables in vars/vars.yml are required:
* `phantom_repo_url` - the URL of the phantom repo installer package for the Phantom version this role will use
* `phantom_community_username` - the username for my.phantom.us which is need to install Phantom
* `phantom_community_pass` - the password for my.phantom.us which is needed to install Phantom
* `phantom_pass` - the password which will be applied as the initial password of the admin user on the Phantom web interface

Dependencies
------------

No known Ansible dependencies

Example Playbook
-------------------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - common
         - phantom

License
-------

BSD

Author Information
------------------

https://www.splunk.com
