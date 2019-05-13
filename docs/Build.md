# Building The Attack Range from Scratch

## Using Packer to Build the Base Image

1. `cd` to the Packer directory and build the Windows 10 machine with the following commands
```
$ cd attack_range/packer
$ packer build --only=virtualbox-iso windows_10.json
```

this might take several hours to complete once done a new .box file will be created under: `packer/windows_10_virtualbox.box`

2. Once the box has been built successfully, make sure you specify your new box file under the **config.vm.box** settings of your target machine file. For example if building windows 10 workstation from scratch run the command above, then edit `windows_workstation/Vagrantfile` under `config.vm.box = ../packer/windows_2016_virtualbox.box` 

3. cd into the root of the the windows_workstation Directory: `cd ../windows_workstation`
4. Install the Vagrant-Reload plugin: `vagrant plugin install vagrant-reload`

## Setup Variables For Ansible

You will need to configure a few variables in the following file

`vars/vars.yml`

By default the Firedrill agent is set to not install. If you want to install it change the following variable (to true) in the vars file
* `install: false` 


### Variables for the Vagrant File
* Update the hostname you would like the VM to have in the Vagrantfile. This is line 1 of the Vagrant file `VM_NAME= "EXAMPLE-HOST-NAME"`

### Variables for Sysmon
By default the install will use a very verbose Sysmon config. If you want to change that keep reading :)

Edit the file vars/vars.yml variable file for which Sysmon config you want
The Sysmon configs are in the roles/install_sysmon/templates directory.



