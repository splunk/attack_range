FROM ubuntu:18.04
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && \
        apt-get install -y python3.8 git unzip python3-pip awscli curl

RUN curl -s https://releases.hashicorp.com/terraform/0.14.4/terraform_0.14.4_linux_amd64.zip -o terraform.zip && \
         unzip terraform.zip && \
         mv terraform /usr/local/bin/

RUN git clone https://github.com/splunk/attack_range.git
RUN echo 'alias python=python3' >> ~/.bashrc

WORKDIR /attack_range

RUN cd terraform/aws/local && terraform init
RUN cd terraform/azure/local && terraform init
RUN pip3 install -r requirements.txt
