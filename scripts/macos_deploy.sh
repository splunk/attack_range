#!/bin/bash
brew update
brew install python awscli python-pip
pip3 install virtualenv
curl -s https://releases.hashicorp.com/terraform/0.14.4/terraform_0.14.4_linux_amd64.zip -o terraform.zip
unzip -o terraform.zip
sudo mv terraform /usr/local/bin/
git clone https://github.com/splunk/attack_range && cd attack_range
cd terraform/aws
terraform init
cd ../..
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
