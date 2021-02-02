#!/bin/bash
brew update
brew install python awscli git terraform
pip3 install virtualenv
git clone https://github.com/splunk/attack_range && cd attack_range
cd terraform/aws
terraform init
cd ../..
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
