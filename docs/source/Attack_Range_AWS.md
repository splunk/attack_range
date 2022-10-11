# Attack Range AWS

## Docker
We built a docker image which you can use to run the attack range code:
````console
docker pull splunk/attack_range
docker run -it splunk/attack_range
aws configure
python attack_range.py configure
````

## MacOS
Install and configure terraform
````console
brew update
brew install terraform
cd terraform/aws && terraform init && cd ../..
````

Install packer
````console
brew tap hashicorp/tap
brew install hashicorp/tap/packer
````

Install awscli
````console
brew install awscli
aws configure
````

Install and run poetry
````console
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
poetry shell
poetry install
````

Configure Attack Range
````console
python attack_range.py configure
````

## Linux
Install some packages
````console
apt-get update
apt-get install -y python3.8 git unzip python3-pip curl
````

Install and configure terraform
````console
curl -s https://releases.hashicorp.com/terraform/1.1.8/terraform_1.1.8_linux_amd64.zip -o terraform.zip && \
unzip terraform.zip && \
mv terraform /usr/local/bin/
````

Install packer
````console
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install packer
````

Install awscli
````console
apt-get install -y awscli
aws configure
````

Install and run poetry
````console
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
poetry shell
poetry install
````

Configure Attack Range
````console
python attack_range.py configure
````

## Windows
We recommend to use the Windows Subsystem for Linux (WSL). You can find a tutorial [here](https://docs.microsoft.com/en-us/windows/wsl/install). After installed WSL, you can follow the steps described in the Linux section.