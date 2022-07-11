# Attack Range Local

## MacOS
Install vagrant and virtualbox
````console
brew update
brew install --cask virtualbox
brew install --cask vagrant
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
Install vagrant and virtualbox
````console
apt-get update
apt-get install virtualbox
wget https://releases.hashicorp.com/vagrant/2.2.19/vagrant_2.2.19_x86_64.deb
apt install ./vagrant_2.2.19_x86_64.deb
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