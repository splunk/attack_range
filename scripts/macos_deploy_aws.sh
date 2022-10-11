#!/bin/bash
brew update
brew install python awscli git terraform
pip3 install virtualenv
git clone https://github.com/splunk/attack_range && cd attack_range
cd terraform/aws/local
terraform init
cd ../../..
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
