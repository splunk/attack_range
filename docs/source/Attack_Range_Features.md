# Attack Range Features

## Cisco Secure Endpoint
A Cisco Secure Endpoint agent can be automatically installed on the Windows server in Attack Range. It is required that the agent is downloaded into the apps folder before running the build command. The logs can ingested automatically to the Splunk server when you enable the Cisco Secure Endpoint log forwarding. You can use the following attack_range.yml configuration:
````yml
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
  cisco_secure_endpoint: "1" # forward cisco secure endpoint logs to splunk
  cisco_secure_endpoint_api_id: ""
  cisco_secure_endpoint_api_secret: ""
windows_servers:
  - hostname: ar-win 
    install_cisco_secure_endpoint: "1"
    cisco_secure_endpoint_windows_agent: "amp_Server.exe"
````
You need to update all the fields with your values.


## CrowdStrike Falcon
A CrowdStrike Falcon agent can be automatically installed on the Windows Servers in Attack Range. It is required that the agent is downloaded into the apps folder before running the build command. The logs can ingested automatically to the Splunk server when you have the CrowdStrike Falcon Data Replicator (FDR) entitlement. You can use the following `attack_range.yml` configuration:
````yml
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
  crowdstrike_falcon: "1" # forward crowdstrike logs to splunk
  crowdstrike_customer_ID: ""
  crowdstrike_logs_region: ""
  crowdstrike_logs_access_key_id: ""
  crowdstrike_logs_secret_access_key: ""
  crowdstrike_logs_sqs_url: ""
windows_servers:
  - hostname: ar-win 
    install_crowdstrike: "1"
    crowdstrike_linux_agent: "falcon-sensor_7.18.0-17106_amd64.deb"
````
You need to update all the fields with your values.


## VMWare Carbon Black Cloud
A Carbon Black agent can be automatically installed on the Windows Servers in Attack Range. It is required that the agent is downloaded into the apps folder before running the build command. The logs can ingested automatically to the Splunk server. You need to configure a Data Forwarder as described [here](https://docs.vmware.com/en/VMware-Carbon-Black-Cloud/services/carbon-black-cloud-user-guide/GUID-E8D33F72-BABB-4157-A908-D8BBDB5AF349.html).
can use the following attack_range.yml configuration:
````yml
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
  carbon_black_cloud: "1" # forward carbon black logs to splunk
  carbon_black_cloud_company_code: ""
  carbon_black_cloud_s3_bucket: ""
windows_servers:
  - hostname: ar-win 
    install_carbon_black: "1"
    carbon_black_windows_agent: "installer_vista_win7_win8-64-4.0.1.1428.msi"
````
You need to update all the fields with your values.


## BadBlood
[BadBlood by Secframe](https://github.com/davidprowe/BadBlood) fills a Microsoft Active Directory Domain with a structure and thousands of objects. The output of the tool is a domain similar to a domain in the real world. After BadBlood is ran on a domain, security analysts and engineers can practice using tools to gain an understanding and prescribe to securing Active Directory. BadBlood can be enabled by setting the parameter bad_blood to 1 as shown in the following example:
````yml
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
windows_servers:
  - hostname: ar-win 
    image: windows-2016-v3-0-0
    create_domain: "1"
    bad_blood: "1"
````


## Guacamole
[Apache Guacamole](https://guacamole.apache.org/) is a clientless remote desktop application which is installed on the Splunk Server. It supports standard protocols such as SSH and RDP. During the Attack Range build, Apache Guacamole is installed and completely configured. You can access Apache Guacamole on port 8080 and use the Attack Range password to log in. Subsequently, you can access the windows server over RDP or the other servers with SSH using the browser.
