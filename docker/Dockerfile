FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && \
        apt-get install -y python3.8 git unzip python3-pip awscli curl vim lsb-release software-properties-common

RUN curl -s https://releases.hashicorp.com/terraform/1.1.8/terraform_1.1.8_linux_amd64.zip -o terraform.zip && \
         unzip terraform.zip && \
         mv terraform /usr/local/bin/

RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | apt-key add -
RUN apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
RUN apt update && apt install packer

RUN git clone -b attack_range_3 https://github.com/splunk/attack_range.git
RUN echo 'alias python=python3' >> ~/.bashrc

WORKDIR /attack_range

RUN cd terraform/aws && terraform init
RUN cd terraform/azure && terraform init
RUN pip3 install poetry
RUN poetry install
RUN pip3 install --upgrade awscli
RUN pip3 install azure-cli
