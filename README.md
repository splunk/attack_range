
![](docs/range.jpg)
# Splunk Attack Range

## Purpose

This framework allows the security analyst to replicate and generate data as close to ground truth as possible, in a format that allows the creation of detections, investigations, knowledge objects, and defense playbooks in Splunk. This data includes things such as logs, network captures and endpoint events derived from either known attack-simulation engines (Atomic Red Team/AttackIQ) or recent exploit code from local (Vagrant) or cloud enviroments (Terraform).
Inspired by [DetectionLab](https://github.com/clong/DetectionLab). 

## Architecture
![Logical Diagram](docs/architecture.png)

## Usage
```
usage: attack_range.py [-h] [-b APPBIN] -m MODE -s STATE [-v VERSION]
                       [-vbox VAGRANT_BOX] [-vls] [-se SIMULATION_ENGINE]

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
  -se SIMULATION_ENGINE, --simulation_engine SIMULATION_ENGINE
                        please select a simulation engine, defaults to
                        "atomic_red_team"
```
## Running

1. `git clone https://github.com/splunk/attack_range && cd attack_range` clone project and cd into the project dir
2. `virtualenv -p python3 venv && source venv/bin/activate && pip install -r requirements.txt` create virtualenv and install requirements
3. `python attack_range.py --state up --mode vagrant` start up a range locally using vagrant or `python attack_range.py --state up --mode terraform` to deploy it to "the cloud"

See [Usage](#usage) for more options, **make sure that you [configure](#configure) the mode first**

if you are on OSX you will have to install sshpass `brew install https://raw.githubusercontent.com/kadwanev/bigboybrew/master/Library/Formula/sshpass.rb`

## Configure 

#### For Terraform
1. `brew install terraform` install terraform CLI on OSX [other platforms](https://www.terraform.io/downloads.html)
2. `brew install awscli`  install aws CLI on OSX otherwise see: [guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
3. Get AWS API token `aws configure` 
4. Set terraform variables under [terraform/terraform.tfvars](https://github.com/splunk/attack_range/blob/develop/terraform/terraform.tfvars.example)

#### For Vagrant
1. `brew install vagrant` install vagrant CLI on OSX otherwise see: [guide](https://www.vagrantup.com/downloads.html)

#### Range Settings
To configure general range settings like your Splunk Server default username, sysmon template to deploy, or Active Directory admin creds edit: [ansible/vars/vars.yml](https://github.com/splunk/attack_range/blob/develop/ansible/vars/vars.yml.default)

## Developing 

1. create virtualenv and install requirements: `virtualenv -p python3 venv && source venv/bin/activate && pip install -r requirements.txt`
2. install pre-commit hooks `pre-commit install`
3. install ansible on osx `brew install ansible`

## Support
You can get help with setting up your own range in the [Splunk Community Slack](http://splk.it/slack). Under the `#security-research` channel.

## Author
* [Jose Hernandez](https://twitter.com/d1vious)

## Contributors
* [Rod Soto](https://twitter.com/rodsoto)
* [Bhavin Patel](https://twitter.com/hackpsy)
* Russ Nolen

## To Do's
* implement Atomic Red Team simulation engine execution
* implement Attack IQ simulation engine execution
* create global conf file
