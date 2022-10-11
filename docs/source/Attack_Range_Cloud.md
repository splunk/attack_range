# Attack Range Cloud

## AWS Cloudtrail
The Attack Range is able to automatically ingest Cloudtrail logs into the Splunk Server of the Attack Range. In order to do that, you need to configure a Cloudtrail. It is describe [here](https://docs.splunk.com/Documentation/AddOns/released/AWS/CloudTrail) in the chapter **Configure AWS services for the CloudTrail input**. You can use the following attack_range.yml configuration to ingest AWS cloudtrail logs:
````
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
aws:
  region: "eu-central-1"
  private_key_path: "~/.ssh/id_rsa"
  cloudtrail: "1"
  cloudtrail_sqs_queue: "https://sqs.us-west-2.amazonaws.com/111111111111/cloudtrail-cloud-attack-range"
````
You need to update the fields attack_range_password, key_name, region, private_key_path, cloudtrail_sqs_queue with your values.


## Azure Logs
The Attack Range is able to automatically ingest Azure logs into the Splunk Server of the Attack Range. Currently Attack Range supports ingesting Azure Activity logs and Eventhub logs. You need to create a service principal with the roles Contributor and Azure Event Hub Receiver. Creating a service principal is described [here](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal). You can use the following attack_range.yml configuration to ingest Azure logs:
````
general:
  attack_range_password: "ChangeMe123!"
  cloud_provider: "aws"
  key_name: "ar"
azure:
  region: "West Europe"
  subscription_id: "xxx"
  private_key_path: "~/.ssh/id_rsa"
  public_key_path: "~/.ssh/id_rsa.pub"
  azure_logging: "1"
  app_id: "xxx"
  client_secret: "xxx"
  tenant_id: "xxx"
  event_hub_name: "xxx"
  event_hub_host_name: "xxx"
````
You need to update all the fields with your values.