
![](docs/range.jpg)
# Splunk Attack Range
  
## Purpose

This lab has been designed with reproducability in mind. Its primary purpose is to allow the user to quickly build various systems (Workstations, Domain Controllers, *nix machines,etc) in a quick and reproducable manner

## Developing 
* For proper installation you will need access to AttackIQ Community Git Lab. See Russ for access

1. create virtualenv and install requirements: `virtualenv -p python3 venv && source venv/bin/activate && pip install -r requirements.txt`

2. install pre-commit hooks `pre-commit install`


## Running hosts

1. `cd windows_workstation` jump into the host folder 
2.  `vagrant up` bring up machine per Vagrantfile settings 
3. `vagrant provision` provision machine per [ansible](ansible/playbooks) playbook 


## Docs

* [Starting](docs/Starting.md)
* [Build](docs/Build.md)
* [To Do's](docs/ToDo.md)