FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && \
        apt-get install -y python3-dev git unzip python3-pip curl vim 

# install aws cli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install && rm "awscliv2.zip"
# install azure cli
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

RUN curl -s https://releases.hashicorp.com/terraform/1.1.8/terraform_1.1.8_linux_amd64.zip -o terraform.zip && \
         unzip terraform.zip && \
         mv terraform /usr/local/bin/

RUN git clone https://github.com/splunk/attack_range.git
RUN echo 'alias python=python3' >> ~/.bashrc

WORKDIR /attack_range
# init terraform files
RUN cd terraform/aws/local && terraform init
RUN cd terraform/azure/local && terraform init
# install python deps
RUN pip install -r requirements.txt
