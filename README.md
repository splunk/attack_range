
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

1. `git clone https://github.com/splunk/attack_range && cd attack_range` clone project and cd into the project dir
2. `virtualenv -p python3 venv && source venv/bin/activate && pip install -r requirements.txt` create virtualenv and install requirements
3. . `python attack_range.py --state up --mode vagrant` start up a range locally using vagrant

See [Usage](#usage) for more options, **make sure that you [configure](#configure) the mode first**

if you are on OSX you will have to install sshpass `brew install https://raw.githubusercontent.com/kadwanev/bigboybrew/master/Library/Formula/sshpass.rb`
## Configure 
#### For Terraform
1. `brew install terraform` install terraform CLI on OSX [other platforms](https://www.terraform.io/downloads.html)
2. `brew install awscli`  install aws CLI on OSX otherwise see: [guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
3. Get AWS API token `aws configure` 
4. Set terraform variables under [terraform/terraform.tfvars](https://github.com/splunk/attack_range/blob/develop/terraform/terraform.tfvars)

#### For Vagrant
1. `brew install vagrant` install vagrant CLI on OSX otherwise see: [guide](https://www.vagrantup.com/downloads.html)

#### Range Settings
To configure general range settings like your Splunk Server default username, sysmon template to deploy, or Active Directory admin creds edit: [ansible/vars/vars.yml](https://github.com/splunk/attack_range/blob/develop/ansible/vars/vars.yml)

## Developing 
* For proper installation you will need access to AttackIQ Community Git Lab. Request access via slack in the #security-content channel

1. create virtualenv and install requirements: `virtualenv -p python3 venv && source venv/bin/activate && pip install -r requirements.txt`
2. install pre-commit hooks `pre-commit install`
3. install ansible on osx `brew install ansible`

## TODO 
* create a cloud attack example using ansible to launch AWS cli commands, use terraform to spin up the attacking host see [here](https://docs.google.com/document/d/1ZLAQ7VQSF1i-Pzq5fw9TFwWnPlaSsj-8GTG0FCVyMe0/edit)
