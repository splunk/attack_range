FROM gitpod/workspace-full:2022-05-08-14-31-53

RUN sudo apt-get update && \
        sudo apt-get install -y python3.8 git unzip python3-pip awscli curl vim lsb-release software-properties-common

RUN sudo curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

RUN brew install terraform

RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add - && \
    sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" && \
    sudo apt-get update && sudo apt-get install packer

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
