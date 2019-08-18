# Building The Attack Range from Scratch

## Using Packer to Build the Base Image

1. `cd` to the Packer directory and build the Windows 10 machine with the following commands
```
$ cd attack_range/Packer
$ packer build --only=virtualbox-iso windows_10.json
```

2. Once the box has been built successfully, move the resulting box (.box file) in the Packer folder to the Boxes folder:

    `mv *.box ../Boxes`

3. cd into the root of the the Workstation Directory: `cd ../Workstation`
4. Install the Vagrant-Reload plugin: `vagrant plugin install vagrant-reload`

## Setup Variables For Ansible

You will need to configure a few variables in the following file

`vars/vars.yml`

The following variables you will need to set in this file

* Splunk Server to send all this to `splunk_uf_server_ip: $SERVER_IP`

By default the Firedrill agent is set to not install. If you want to install it change the following variable (to true) in the vars file
* `install: false` 

### Variables for the Vagrant File
* Update the hostname you would like the VM to have in the Vagrantfile. This is line 1 of the Vagrant file `VM_NAME= "EXAMPLE-HOST-NAME"`

### Variables for Sysmon
By default the install will use a very verbose Sysmon config. If you want to change that keep reading :)

Edit the file vars/vars.yml variable file for which Sysmon config you want
The Sysmon configs are in the roles/install_sysmon/templates directory.


