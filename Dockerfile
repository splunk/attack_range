FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y python3.10 git unzip python3-pip awscli curl vim lsb-release software-properties-common

RUN curl -s https://releases.hashicorp.com/terraform/1.9.6/terraform_1.9.6_linux_amd64.zip -o terraform.zip && \
         unzip terraform.zip && \
         mv terraform /usr/local/bin/

RUN echo 'alias python=python3' >> ~/.bashrc

RUN mkdir -p /attack_range
COPY configs/ /attack_range/configs/
COPY modules/ /attack_range/modules/
COPY terraform/ /attack_range/terraform/
RUN mkdir -p /attack_range/apps/
COPY pyproject.toml attack_range.py attack_range.yml README.md LICENSE /attack_range/

WORKDIR /attack_range

RUN cd terraform/aws && terraform init
RUN cd terraform/azure && terraform init
RUN pip3 install poetry
RUN poetry install 
RUN pip3 install --upgrade awscli requests
RUN pip3 install azure-cli

COPY docker-entrypoint.sh ./
RUN chmod +x ./docker-entrypoint.sh
CMD ["./docker-entrypoint.sh"]