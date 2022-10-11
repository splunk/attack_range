# Attack Range Features

## Fast build time with packer
Attack Range supports to prebuilt images and therefore improve the build time to 5 minutes. You can use the following attack_range.yml configuration as an example:
````
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
  use_prebuilt_images_with_packer: "1"
windows_servers:
  - hostname: ar-win 
    image: windows-2016-v3-0-0
````

## Crowdstrike Falcon
A Crowdstrike Falcon agent can be autmatically installed on the Windows Servers in Attack Range. It is required that the agent is downloaded into the apps folder before running the build command. The logs can ingested automatically to the Splunk server when you have the Crowdstrike Falcon Data Replicator (FDR) entitlement. You can use the following attack_range.yml configuration:
````
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
  crowdstrike_falcon: "1"
  crowdstrike_agent_name: "WindowsSensor.exe"
  crowdstrike_customer_ID: ""
  crowdstrike_logs_region: ""
  crowdstrike_logs_access_key_id: ""
  crowdstrike_logs_secret_access_key: ""
  crowdstrike_logs_sqs_url: ""
windows_servers:
  - hostname: ar-win 
    image: windows-2016-v3-0-0
````
You need to update all the fields with your values.


## VMWare Carbon Black Cloud
A Carbon Black agent can be autmatically installed on the Windows Servers in Attack Range. It is required that the agent is downloaded into the apps folder before running the build command. The logs can ingested automatically to the Splunk server. You need to configure a Data Forwarder as described [here](https://docs.vmware.com/en/VMware-Carbon-Black-Cloud/services/carbon-black-cloud-user-guide/GUID-E8D33F72-BABB-4157-A908-D8BBDB5AF349.html).
can use the following attack_range.yml configuration:
````
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
  carbon_black_cloud: "1"
  carbon_black_cloud_agent_name: "installer_vista_win7_win8-64-3.8.0.627.msi"
  carbon_black_cloud_company_code: ""
  carbon_black_cloud_s3_bucket: ""
windows_servers:
  - hostname: ar-win 
    image: windows-2016-v3-0-0
````
You need to update all the fields with your values.


## BadBlood
BadBlood by Secframe fills a Microsoft Active Directory Domain with a structure and thousands of objects. The output of the tool is a domain similar to a domain in the real world. After BadBlood is ran on a domain, security analysts and engineers can practice using tools to gain an understanding and prescribe to securing Active Directory. BadBlood can be enabled by setting the parameter bad_blood to 1 as shown in the following example:
````
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
