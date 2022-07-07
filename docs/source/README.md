<p align="center">
    <a href="https://github.com/splunk/attack_range/releases">
        <img src="https://img.shields.io/github/v/release/splunk/attack_range" /></a>
    <a href="https://github.com/splunk/attack_range/actions">
        <img src="https://github.com/splunk/attack_range/actions/workflows/nightly-build-attack-destroy.yml/badge.svg?branch=develop"/></a>
    <a href="https://github.com/splunk/attack_range/graphs/contributors" alt="Contributors">
        <img src="https://img.shields.io/github/contributors/splunk/attack_range" /></a>
    <a href="https://github.com/splunk/attack_range/stargazers">
        <img src="https://img.shields.io/github/stars/splunk/attack_range?style=social" /></a>
</p>

# Home
![Attack Range Log](https://raw.githubusercontent.com/splunk/attack_range/develop/docs/attack_range.png)
The Attack Range is a detection development platform, which solves three main challenges in detection engineering:
* The user is able to quickly build a small lab infrastructure as close as possible to a production environment.
* The Attack Range performs attack simulation using different engines such as Atomic Red Team or Caldera in order to generate real attack data. 
* It integrates seamlessly into any Continuous Integration / Continuous Delivery (CI/CD) pipeline to automate the detection rule testing process.  

The Attack Range uses packer to build golden images and then use terraform and ansible to build it. In the first run, it will take around 20 min per server. After that, you can build Attack Ranges within 5 minutes and less because you already
have the golden images.

# Getting Started

## Build Attack Range
 - MacOs
 - Linux (AWS)
    1. `source <(curl -s 'https://raw.githubusercontent.com/splunk/attack_range/develop/scripts/ubuntu_deploy.sh')`
    2. `aws configure`
    3. `python attack_range.py configure`
 - Windows 
 - Docker (AWS)
    1. `docker pull splunk/attack_range`
    2. `docker run -it splunk/attack_range`
    3. `aws configure`  
    4. `python attack_range.py configure` 

To install directly on Ubuntu, MacOS follow [these](https://github.com/splunk/attack_range/wiki/Installing-on-Ubuntu-or-MacOS) instructions.

## Control Attack Range
 - Pause
    ```
      python attack_range.py pause
    ```
 - Resume
    ```
      python attack_range.py resume
    ```
 - Destroy
    ```
      python attack_range.py destroy
    ```

## Simulate Attacks
 - Atomic Red Team
 - PurpleSharp
 - Prelude
 - Kali Linux

## Dump Attack Data
### Dump Log Data from Attack Range
```
python attack_range.py dump --file_name attack_data/dump.log --search 'index=win' --earliest 2h
```

## Replay Attack Data
### Replay Dumps into Attack Range Splunk Server
```
python attack_range.py replay --file_name attack_data/dump.log --source test --sourcetype test
```

# Cost Explorer
 - AWS
 - Azure