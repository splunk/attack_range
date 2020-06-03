![](docs/range.png)
# Splunk Attack Range

| branch | build status |
| ---    | ---          |
| develop| [![develop status](https://circleci.com/gh/splunk/attack_range/tree/develop.svg?style=svg&circle-token=67ad1fa7779c57d7e5bcfc42bd617baf607ec269)](https://circleci.com/gh/splunk/attack_range/tree/develop)|
| master | [![master status](https://circleci.com/gh/splunk/attack_range/tree/master.svg?style=svg&circle-token=67ad1fa7779c57d7e5bcfc42bd617baf607ec269)](https://circleci.com/gh/splunk/attack_range/tree/master)|

## Purpose
The Attack Range is a detection development platform, which solves three main challenges in detection engineering. First, the user is able to build quickly a small lab infrastructure as close as possible to a production environment. Second, the Attack Range performs attack simulation using different engines such as Atomic Red Team or Caldera in order to generate real attack data. Third, it integrates seamlessly into any Continuous Integration / Continuous Delivery (CI/CD) pipeline to automate the detection rule testing process.  


## Demo
[:tv: A short demo (< 6 min)](https://www.youtube.com/watch?v=xIbln7OQ-Ak) which shows the basic functions of the attack range. It builds a testing enviroment using terraform, walks through the data collected by Splunk. Then attacks it using MITRE ATT&CK Technique [T1003](https://attack.mitre.org/techniques/T1003/) and finally showcases how [ESCU](https://github.com/splunk/security-content) searches are used to detect the attack.

[![Attack Range Demo](https://img.youtube.com/vi/xIbln7OQ-Ak/0.jpg)](https://www.youtube.com/watch?v=xIbln7OQ-Ak)

## Deployment

Attack Range can be built in three different ways:

- **local** using vagrant and virtualbox
- in the **cloud** using terraform and AWS
- **cloud optimized** using terraform, packer and AWS

![Logical Diagram](docs/attack_range_architecture1.png)

## Architecture

The Attack Range can build:
- virtualized deployments with AWS EC2 or local with vagrant/virtualbox
- container deployments with AWS EKS using Kubernetes
- serverless deployments using AWS Lambda, REST API, S3 and DynamoDB

![Logical Diagram](docs/attack_range_architecture.png)

### Virtualized Deployment

#### Architecture

The virtualized deployment of Attack Range consists of:

- Windows Domain Controller
- Windows Server
- Windows Workstation
- A Kali Machine
- Splunk Server
- Phantom Server

Which can be added/removed/configured using [attack_range.conf](attack_range.conf). More machines such as Phantom, Linux server, Linux client, MacOS clients are currently under development.

![Logical Diagram](docs/attack_range_architecture2.png)

An approxiamte **cost estimate** for running attack_range using `--mode terraform` on AWS can be found [here](https://github.com/splunk/attack_range/wiki/Cost-Estimates---mode-terraform).

#### Logging
The following log sources are collected from the machines:
- Windows Event Logs (```index = win```)
- Sysmon Logs (```index = win```)
- Powershell Logs (```index = win```)
- Network Logs with Splunk Stream (```index = main```)
- Attack Simulation Logs from Atomic Red Team and Caldera (```index = attack```)


### Container Deployment with Kubernetes

#### Architecture

The container deployment consists of two worker nodes and one master node in Kubernetes. Deploying a Kubernetes cluster can be activated in [attack_range.conf](attack_range.conf) with the key kubernetes. Additionally, an application is deployed to the Kubernetes cluster which can be configured in [attack_range.conf](attack_range.conf). In the default settings, a wordpress application is deployed to the Kubernetes cluster.

#### Logging
[Splunk Connect for Kubernetes](https://github.com/splunk/splunk-connect-for-kubernetes) is deployed in order to collect logs from the Kubernetes cluster. The Kubernetes logs can be found in the index ```index = kubernetes OR index = kubernetes-metrics``` on the Splunk instance.


### Serverless Deployment

#### Architecture

The serverless deployment consists of Lambda, REST API, S3 and DynamoDB in AWS. Deploying a serverless infrastructure can be activated in [attack_range.conf](attack_range.conf) with the key cloud_attack_range. An application is needed for the serverless application, whereby the author build an own backend application running in Lambda and leverage the REST API and DynamoDB. More information can be found [here](https://github.com/splunk/attack_range/wiki/Serverless-Deployment).

#### Logging

The main log sources for the serverless deployment are CloudWatch and CloudTrail. CloudWatch contains logs for Lambda and REST API. CloudTrail monitors AWS account activities. CloudTrail can be enabled/disabled separatley. CloudTrail will monitor all the account activities for the used AWS account and can't be limited to the Attack Range infrastructure only. Please make sure that you are allowed to use these logs. The serverless deplyoment logs can be found in the index ```index = aws``` on the Splunk instance.


## Configuration
- local [Vagrant and Virtualbox](https://github.com/splunk/attack_range/wiki/Configure-Attack-Range-for-Vagrant)
- cloud [Terraform and AWS](https://github.com/splunk/attack_range/wiki/Configure-Attack-Range-for-Terraform)
- cloud optimized [Packer + Terraform and AWS](https://github.com/splunk/attack_range/wiki/Configure-Attack-Range-for-Packer)

## Running
Attack Range supports different actions:
- Build Attack Range
- Perform Attack Simulation
- Search with Attack Range
- Destroy Attack Range
- Stop Attack Range
- Resume Attack Range

### Build Attack Range
- Build Attack Range
```
python attack_range.py -m terraform/vagrant -a build
```

### Perform Attack Simulation
- Perform Attack Simulation
```
python attack_range.py -m terraform/vagrant -a simulate -st T1117,T1003 -t attack-range-windows-domain-controller
```

### Search with Attack Range
- Run a savedsearch and return the results
```
python attack_range.py -m terraform/vagrant -a search -sn search_name
```

### Destroy Attack Range
- Destroy Attack Range
```
python attack_range.py -m terraform/vagrant -a destroy
```

### Stop Attack Range
- Stop Attack Range
```
python attack_range.py -m terraform/vagrant -a stop
```

### Resume Attack Range
- Resume Attack Range
```
python attack_range.py -m terraform/vagrant -a resume
```

## Cloud Optimized
Using the Attack Range for automated detection testing in a Continuous Integration (CI) pipeline, needs the ability to build it quickly. Therefore we introduced the mode cloud optimized by combining [packer](https://packer.io/) and [terraform](https://www.terraform.io/). In this mode you need to build the AMIs with packer and then use terraform with the prebuilt AMIs:

- Build AMIs with packer
```
python attack_range.py -m packer -a build_amis
```

- Build Attack Range with terraform and -ami flag:
```
python attack_range.py -m terraform -a build -ami
```

- Deregister AMIs with packer
```
python attack_range.py -m packer -a destroy_amis
```


## Features
- [Splunk Server](https://github.com/splunk/attack_range/wiki/Splunk-Server)
  * Indexing of Microsoft Event Logs, PowerShell Logs, Sysmon Logs, DNS Logs, ...
  * Preconfigured with multiple TAs for field extractions
  * Out of the box Splunk detections with Enterprise Security Content Update ([ESCU](https://splunkbase.splunk.com/app/3449/)) App
  * Preinstalled Machine Learning Toolkit ([MLTK](https://splunkbase.splunk.com/app/2890/))
  * Splunk UI available through port 8000 with user admin
  * ssh connection over configured ssh key

- [Splunk Enterprise Security](https://splunkbase.splunk.com/app/263/)
  * [Splunk Enterprise Security](https://splunkbase.splunk.com/app/263/) is a premium security solution requiring a paid license.
  * Enable or disable [Splunk Enterprise Security](https://splunkbase.splunk.com/app/263/) in [attack_range.conf](attack_range.conf)
  * Purchase a license, download it and store it in the apps folder to use it.

- [Splunk Phantom](https://www.splunk.com/en_us/software/splunk-security-orchestration-and-automation.html)
  * [Splunk Phantom](https://www.splunk.com/en_us/software/splunk-security-orchestration-and-automation.html) is a Security Orchestration and Automation platform
  * For a free development license (100 actions per day) register [here](https://my.phantom.us/login/?next=/)
  * Enable or disable [Splunk Phantom](https://www.splunk.com/en_us/software/splunk-security-orchestration-and-automation.html) in [attack_range.conf](attack_range.conf)

- [Splunk Mission Control (BETA)](https://www.splunk.com/en_us/form/splunk-mission-control.html)
  * Splunk Mission Control is a unified experience that modernizes and optimizes your team’s security operations. The cloud-based software-as-a-service (SaaS) allows you to detect, manage, investigate, hunt, contain, and remediate threats and other high-priority security issues across the entire event lifecycle—all from the common work surface it provides.
  * Instructions on how to configure mission control and run a demo can be found [here](https://github.com/splunk/attack_range/wiki/Demo:-Splunk-Mission-Control).

- [Splunk Data Stream Processor](https://www.splunk.com/en_us/software/stream-processing.html)
  * Splunk Data Stream Processor is a scalable stream processing solution built to guarantee delivery of high-volume, high-velocity data across the enterprise. As events occur, DSP continuously collects, formats, and organizes high-velocity, high-volume data based on specified conditions, masks sensitive or private information, detects abnormal data patterns, and then distributes results to Splunk or other destinations in milliseconds
  * Instructions on how to configure Splunk DSP can be found [here](https://github.com/splunk/attack_range/wiki/Output-to-Splunk-DSP-(Data-Stream-Processing)).

- [Windows Domain Controller & Window Server & Windows 10 Client](https://github.com/splunk/attack_range/wiki/Windows-Infrastructure)
  * Can be enabled, disabled and configured over [attack_range.conf](attack_range.conf)
  * Collecting of Microsoft Event Logs, PowerShell Logs, Sysmon Logs, DNS Logs, ...
  * Sysmon log collection with customizable Sysmon configuration
  * RDP connection over port 3389 with user Administrator

- [Atomic Red Team](https://github.com/redcanaryco/atomic-red-team)
  * Attack Simulation with [Atomic Red Team](https://github.com/redcanaryco/atomic-red-team)
  * Will be automatically installed on target during first execution of simulate

- [Caldera](https://github.com/mitre/caldera)
  * Adversary Emulation with [Caldera](https://github.com/mitre/caldera)
  * Installed on the Splunk Server and available over port 8888 with user admin
  * Preinstalled Caldera agents on windows machines

- [Kali Linux](https://www.kali.org/)
  * Preconfigured Kali Linux machine for penetration testing
  * ssh connection over configured ssh key


## Demo Mode
We are using Attack Range to test and demo specific attack scenarios. We want to share them with the community. The [attack_range.conf](attack_range.conf) has an option run_demo and demo_scenario. We currently support the following demo scenario:
- demo_scenario: mission_control_malicious_putty. In this scenario, the windows server contains a backdoored version of putty.exe called puttyX.exe located in the C drive. When the user clicks on it a reverse meterpreter shell is established to the kali linux. Then, kali linux will perform enumeration and credential dumping with hashdump and mimikatz. These credentials are used by kali linux to copy the malicious puttyX.exe from the windows domain controller to the windows server.



## Planned features
- Linux Server
- Linux Client
- macOS Client


## Support
Please use the [GitHub issue tracker](https://github.com/splunk/attack_range/issues) to submit bugs or request features.

If you have questions or need support, you can:

* Post a question to [Splunk Answers](http://answers.splunk.com)
* Join the [#security-research](https://splunk-usergroups.slack.com/messages/C1RH09ERM/) room in the [Splunk Slack channel](http://splunk-usergroups.slack.com)
* If you are a Splunk Enterprise customer with a valid support entitlement contract and have a Splunk-related question, you can also open a support case on the https://www.splunk.com/ support portal


## Author
* [Jose Hernandez](https://twitter.com/d1vious)
* [Patrick Bareiß](https://twitter.com/bareiss_patrick)

## Contributors
* [Bhavin Patel](https://twitter.com/hackpsy)
* [Rod Soto](https://twitter.com/rodsoto)
* Russ Nolen
* Phil Royer
* [Joseph Zadeh](https://twitter.com/JosephZadeh)
* Rico Valdez
* [Dimitris Lambrou](https://twitter.com/etz69)
* [Dave Herrald](https://twitter.com/daveherrald)

## Contributing
We welcome feedback and contributions from the community! Please see our [contribution guidelines](docs/CONTRIBUTING.md) for more information on how to get involved.
