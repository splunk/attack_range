#!/bin/bash
brew update
brew install python azure-cli git terraform
pip3 install virtualenv
git clone https://github.com/splunk/attack_range && cd attack_range
cd terraform/azure
terraform init
cd ../..
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
