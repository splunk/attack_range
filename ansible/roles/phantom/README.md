Role Name
========

Install a Phantom server from RPMs on CentOS/RHEL 7

Requirements
------------

The user-specific file ~/.attack_range.yml must be created and populated with my.phantom.us credentials and a user-specified initial password for the Phantom instance. If you don't have an account on my.phantom.us go ahead and sign up for free: https://my.phantom.us/signup/

Role Variables
--------------

The following variables must be declared in ~/.attack_range.yml:
* `phantom_community_user` - the username for my.phantom.us which is need to install Phantom
* `phantom_community_pass` - the password for my.phantom.us which is needed to install Phantom
* `phantom_pass` - pick a random password which will be applied as the initial password of the admin user on the Phantom web interface

The following variable in vars/vars.yml is required:
* `phantom_repo_url` - the URL of the phantom yum repository installer package for the Phantom version that will be used by this role

Dependencies
------------

No known Ansible dependencies

Example Playbook
-------------------------

To use this role just populate vars/vars.yml and apply the role like so:

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
