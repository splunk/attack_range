# Attack Range Local

## MacOS
Clone the [Attack Range]() git repo to your local machine, and open the folder:
````bash
git clone https://github.com/splunk/attack_range.git
cd attack_range
````

Install [Vagrant](https://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/):
````bash
brew update
brew install --cask virtualbox
brew install --cask vagrant
````

Install and run [Poetry](https://github.com/python-poetry/poetry):
````bash
curl -sSL https://install.python-poetry.org/ | python -
poetry shell
poetry install
````

Configure Attack Range:
````bash
python attack_range.py configure
````

## Linux
Clone the [Attack Range]() git repo to your local machine, and open the folder:
````bash
git clone https://github.com/splunk/attack_range.git
cd attack_range
````

Install [Vagrant](https://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/):
````bash
apt-get update
apt-get install virtualbox
wget https://releases.hashicorp.com/vagrant/2.2.19/vagrant_2.2.19_x86_64.deb
apt install ./vagrant_2.2.19_x86_64.deb
````

Install and run [Poetry](https://github.com/python-poetry/poetry):
````bash
curl -sSL https://install.python-poetry.org/ | python -
poetry shell
poetry install
````

Configure Attack Range:
````bash
python attack_range.py configure
````
