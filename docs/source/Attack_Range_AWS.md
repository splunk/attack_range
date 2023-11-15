# Attack Range AWS

## Docker
We built a docker image which you can use to run the attack range code:
````bash
docker pull splunk/attack_range
docker run -it splunk/attack_range
aws configure
python attack_range.py configure
````

## MacOS
Clone attack_range git repo to local machine
````bash
git clone https://github.com/splunk/attack_range.git
cd attack_range
````

Install and configure terraform
````bash
brew update
brew install terraform
cd terraform/aws && terraform init && cd ../..
````

Install packer
````bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer
````

Install awscli
````bash
brew install awscli
aws configure
````

Install and run poetry
````bash
curl -sSL https://install.python-poetry.org/ | python -
poetry shell
poetry install
````

Configure Attack Range
````bash
python attack_range.py configure
````

## Linux
Install some packages
````bash
apt-get update
apt-get install -y python3.8 git unzip python3-pip curl
````
Clone attack_range git repo to local machine
````bash
git clone https://github.com/splunk/attack_range.git
cd attack_range
````

Install and configure terraform
````bash
curl -s https://releases.hashicorp.com/terraform/1.1.8/terraform_1.1.8_linux_amd64.zip -o terraform.zip && \
unzip terraform.zip && \
mv terraform /usr/local/bin/
````

Install packer
````bash
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install packer
````

Install awscli
````bash
apt-get install -y awscli
aws configure
````

Install and run poetry
````bash
curl -sSL https://install.python-poetry.org/ | python -
poetry shell
poetry install
````

Configure Attack Range
````bash
python attack_range.py configure
````

## Windows
We recommend to use the Windows Subsystem for Linux (WSL). You can find a tutorial [here](https://docs.microsoft.com/en-us/windows/wsl/install). After installed WSL, you can follow the steps described in the Linux section.
