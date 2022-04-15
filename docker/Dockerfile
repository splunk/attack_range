FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && \
        apt-get install -y python3.8 git unzip python3-pip awscli curl vim 

RUN curl -s https://releases.hashicorp.com/terraform/1.1.8/terraform_1.1.8_linux_amd64.zip -o terraform.zip && \
         unzip terraform.zip && \
         mv terraform /usr/local/bin/

RUN git clone https://github.com/splunk/attack_range.git
RUN echo 'alias python=python3' >> ~/.bashrc

WORKDIR /attack_range

RUN cd terraform/aws/local && terraform init
RUN cd terraform/azure/local && terraform init
RUN pip3 install -r requirements.txt
#fixes a known issue with AWS CLI on Ubuntu 20.04
#https://github.com/aws-solutions/aws-control-tower-customizations/issues/34
RUN pip3 install --upgrade awscli
