# Attack Range Local

## MacOS
Clone attack_range git repo to local machine
````console
git clone https://github.com/splunk/attack_range.git
cd attack_range
````

Install vagrant and virtualbox
````console
brew update
brew install --cask virtualbox
brew install --cask vagrant
````

Install and run poetry
````console
curl -sSL https://install.python-poetry.org/ | python -
poetry shell
poetry install
````

Configure Attack Range
````console
python attack_range.py configure
````

## Linux
Clone attack_range git repo to local machine
````console
git clone https://github.com/splunk/attack_range.git
cd attack_range
````

Install vagrant and virtualbox
````console
apt-get update
apt-get install virtualbox
wget https://releases.hashicorp.com/vagrant/2.2.19/vagrant_2.2.19_x86_64.deb
apt install ./vagrant_2.2.19_x86_64.deb
````

Install and run poetry
````console
curl -sSL https://install.python-poetry.org/ | python -
poetry shell
poetry install
````

Configure Attack Range
````console
python attack_range.py configure
````
