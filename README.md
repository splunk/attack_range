
![](docs/range.jpg)
# Splunk Attack Range

## Purpose
The Attack Range solves two main challenges in development of detections. First, it allows the user to quickly build a small lab infrastructure as close as possible to your production environment. This lab infrastructure contains a Windows Domain Controller, Windows Workstation and Linux server, which comes pre-configured with multiple security tools and logging configuration. The infrastructure comes with a Splunk server collecting multiple log sources from the servers and normalizing them according to the [Common Information Model](https://docs.splunk.com/Documentation/CIM/4.14.0/User/Overview).  

Second, this framework allows the user to perform attack simulation using different engines. Therefore, the user can repeatedly replicate and generate data as close to "ground truth" as possible, in a format that allows the creation of detections, investigations, knowledge objects, and playbooks in Splunk.


## Architecture
Attack Range can be used in two different ways:
- local using vagrant and virtualbox
- in the cloud using terraform and AWS

In order to make Attack Range work on almost every laptop, the local version using Vagrant and Virtualbox consists of a subset of the full-blown cloud infrastructure in AWS using Terraform. The local version consists of a Splunk single instance and a Windows 10 workstation pre-configured with best practice logging configuration according to Splunk. The cloud infrastructure in AWS using Terraform consists of a Windows 10 workstation, a Windows 2016 server and a Splunk server. More information can be found in the wiki

![Logical Diagram](docs/architecture.png)


## Configuration
- [vagrant and virtualbox](https://github.com/splunk/attack_range/wiki/Configure-Attack-Range-for-Vagrant)
- [terraform and AWS](https://github.com/splunk/attack_range/wiki/Configure-Attack-Range-for-Terraform)

## Running
In order to use Attack Range, two steps needs to be performed:
1. Build Attack Range
2. Perform Attack Simulation
3. Destroy Attack Range

### Build Attack Range
- Build Attack Range using **Terraform**
```
python attack_range.py -m terraform -a build
```
- Build Attack Range using **Vagrant**
```
python attack_range.py -m vagrant -a build
```

### Perform Attack Simulation


### Destroy Attack Range
- Destroy Attack Range using **Terraform**
```
python attack_range.py -m terraform -a destroy
```
- Destroy Attack Range using **Vagrant**
```
python attack_range.py -m vagrant -a destroy
```

## Support
You can get help with setting up your own attack range in the [Splunk Community Slack](http://splk.it/slack) under the `#security-research` channel.

## Author
* [Jose Hernandez](https://twitter.com/d1vious)

## Contributors
* [Rod Soto](https://twitter.com/rodsoto)
* [Bhavin Patel](https://twitter.com/hackpsy)
* [Patrick Bareiß](https://twitter.com/bareiss_patrick)
* Russ Nolen

## Acknowledgements
- [DetectionLab](https://github.com/clong/DetectionLab)
- Atomic Red team
- Sysmon configuration

