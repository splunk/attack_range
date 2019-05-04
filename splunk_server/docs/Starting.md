# Bringing the Machine Up

Vagrant commands must be run from the Workstation directory where the Vagrantfile is located.

Once the box file is built and moved into the Boxes directory you simply issues the `vagrant up` command. During first boot the machine will reboot a few times and then the ansible playbooks will be run. You will be left with a fully functioning machine with the needed tooling 

## Basic Vagrant Usage 

* Bring up the windows workstation host(s): `vagrant up` 
 
* Run just the provisioning on the windows workstation host(s): `vagrant provision`
* Restarting of the windows workstation host(s) and re-run the provision process: `vagrant reload <hostname> --provision`
* Restart of the windows workstation host(s) `vagrant reload <hostname>`
* Check of the windows workstation host(s): `vagrant status`
* Suspend the windows workstation host(s): `vagrant suspend`
* Resume the windows workstation host(s): `vagrant resume`
* Bring up the windows workstation host(s): `vagrant up <hostname>`
* Creating a snapshot of the windows workstation host(s): `vagrant snapshot save $name_of_VM $name_of_snapshot`
* Restoring a snapshot of the windows workstation host(s): `vagrant snapshot restore $name_of_VM $name_of_snapshot`
