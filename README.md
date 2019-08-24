
![](docs/range.jpg)
# Splunk Attack Range
  
## Purpose

This lab has been designed with reproducability in mind. Its primary purpose is to allow the user to quickly build various systems (Workstations, Domain Controllers, *nix machines,etc) in a quick and reproducable manner

## Usage
```
usage: attack_range.py [-h] [-b APPBIN] -m MODE -s STATE [-v VERSION]
                       [-vbox VAGRANT_BOX] [-vls]

starts a attack range ready to collect attack data into splunk

optional arguments:
  -h, --help            show this help message and exit
  -b APPBIN, --appbin APPBIN
                        directory to store binaries in
  -m MODE, --mode MODE  mode of operation, terraform/vagrant, please see
                        configuration for each at:
                        https://github.com/splunk/attack_range
  -s STATE, --state STATE
                        state of the range, defaults to "up", up/down allowed
  -v VERSION, --version VERSION
                        shows current attack_range version
  -vbox VAGRANT_BOX, --vagrant_box VAGRANT_BOX
                        select which vagrant box to stand up or destroy
                        individually
  -vls, --vagrant_list  prints out all avaiable vagrant boxes
```
## Running

1. `virtualenv -p python3 venv && source venv/bin/activate && pip install -r requirements.txt` create virtualenv and install requirements: 
2. `python attack_range.py --state up --mode vagrant`

See [Usage](#usage) for more options, make sure that you [configure](#configure) your mode first

## Configure 
#### For Terraform
1. `brew install terraform` install terraform CLI _on osx** [other platforms](https://www.terraform.io/downloads.html)
2. `brew install awscli`  install aws CLI _on osx_ otherwise see: [guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
2. Get AWS API token `aws configure` 

#### For Vagrant
1. `brew install vagrant` install vagrant CLI _on osx_ otherwise see: [guide](https://www.vagrantup.com/downloads.html)

## Developing 
* For proper installation you will need access to AttackIQ Community Git Lab. Request access via slack in the #security-content channel

1. create virtualenv and install requirements: `virtualenv -p python3 venv && source venv/bin/activate && pip install -r requirements.txt`

2. install pre-commit hooks `pre-commit install`
3. install ansible  _on osx_ `brew install ansible`
