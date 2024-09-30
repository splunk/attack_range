FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt update && apt upgrade -y
RUN apt-get install -y software-properties-common
RUN apt update
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update
RUN apt install -y python3.12

RUN apt-get install -y git unzip python3-pip curl vim 

RUN curl -s https://releases.hashicorp.com/terraform/1.9.6/terraform_1.9.6_linux_amd64.zip -o terraform.zip && \
         unzip terraform.zip && \
         mv terraform /usr/local/bin/

RUN echo 'alias python=python3.12' >> ~/.bashrc

RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.12 get-pip.py && \
    rm get-pip.py
RUN python3.12 -m pip install --upgrade setuptools wheel

RUN python3.12 -m pip install --upgrade pip

RUN python3.12 -m pip install --upgrade awscli azure-cli

RUN git clone https://github.com/splunk/attack_range.git

WORKDIR /attack_range

RUN python3.12 -m pip install -r requirements.txt

