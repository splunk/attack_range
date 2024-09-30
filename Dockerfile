FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y python3.10 git unzip python3-pip curl vim lsb-release software-properties-common

RUN curl -s https://releases.hashicorp.com/terraform/1.9.6/terraform_1.9.6_linux_amd64.zip -o terraform.zip && \
         unzip terraform.zip && \
         mv terraform /usr/local/bin/

RUN echo 'alias python=python3' >> ~/.bashrc

RUN pip3 install poetry
RUN pip3 install --upgrade awscli requests
RUN pip3 install azure-cli

RUN git clone https://github.com/splunk/attack_range.git
COPY requirements.txt /attack_range/requirements.txt


WORKDIR /attack_range

RUN pip3 install -r requirements.txt
