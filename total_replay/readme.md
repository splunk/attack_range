# TOTAL-REPLAY

![TOTAL-REPLAY](assets/banner.png)

## Description

This lightweight tool helps you make the most of Splunk’s [Security Content](https://github.com/splunk/security_content) metadata, such as detection names, analytic stories, and more, by replaying relevant test event logs or attack data from either the [Splunk Attack Data](https://github.com/splunk/attack_data) or [Splunk Attack Range](https://github.com/splunk/attack_range) projects.

## Installation

### MAC/LINUX:

**How to install TOTAL-REPLAY when working with Splunk Attack Range or Splunk Attack Data**

#### TOTAL-REPLAY IN SPLUNK ATTACK-RANGE REPO:
---

1. Clone the Splunk Security Content github repo. We recommend to follow this steps [Security Content Getting Started](https://github.com/splunk/security_content).

2. We recommend following the instructions in the [Attack Range Getting Started](https://github.com/splunk/attack_range)
 guide. Once Attack Range is installed and its virtual environment (managed via Poetry) is activated, TOTAL-REPLAY is almost ready to use — you just need to configure it.

3. In total_replay->configuration->config.yml, add the folder path of the Splunk Attack Data repo and the detection folder path in Splunk Security Content.

```
settings:
  security_content_detection_path: ~/path/to/your/security_content/detections
  attack_range_dir_path: ~/path/to/your/attack_range
```

4. enable the `attack_range_version_on` config setting in total_replay->configuration->config.yml:
   **NOTE: You can enable  either `attack_range_version_on` or `attack_data_version_on` settings**
```
attack_range_version_on: True
```

#### TOTAL-REPLAY IN SPLUNK ATTACK-DATA REPO:
---

1. Clone the Splunk Attack Data github repo. We recommend to follow this steps [Attack Data Getting Started](https://github.com/splunk/attack_data/).

2. Clone the Splunk Security Content github repo. We recommend to follow this steps [Security Content Getting Started](https://github.com/splunk/security_content).

3. Install Poetry (if not already installed)
```
curl -sSL https://install.python-poetry.org/ | python3 -
```
4. Navigate to your project directory
```
cd /path/to/your/total-replay-project
```
5. Create a virtual environment and activate it
```
poetry shell
```
6. Install project dependencies

7. In total_replay->configuration->config.yml, add the folder path of the Splunk Attack Data repo and the detection folder path in Splunk Security Content.

```
settings:
  security_content_detection_path: ~/path/to/your/security_content/detections
  attack_data_dir_path: ~/path/to/your/attack_data
```
8. enable the `attack_data_version_on` config setting in total_replay->configuration->config.yml:
   **NOTE: You can enable  either `attack_range_version_on` or `attack_data_version_on` settings**
```
attack_data_version_on: True
```

9. make sure you setup the required environment variables for splunk server connection

    | Environment Variables.     | Description             |
    |----------------------------|-------------------------|
    | **SPLUNK_HOST**            | SPLUNK HOST IP ADDRESS  |
    | **SPLUNK_HEC_TOKEN**       | SPLUNK SERVER HEC TOKEN |

    you can use the `export` commandline function for adding these environment variables

    ```
    export SPLUNK_HOST= <IP_ADDRESS>
    export SPLUNK_HEC_TOKEN= <SPLUNK_HEC_TOKEN>
    ```

### Windows OS:

We recommend using the Windows Subsystem for Linux (WSL). You can find a tutorial [here](https://learn.microsoft.com/en-us/windows/wsl/install). After installing WSL, you can follow the steps described in the Linux section.


### OPTIONAL:
- You can toggle the `debug_print` configuration setting of TOTAL-REPLAY to disable or enable debug print during execution.


## Usage

![TOTAL-REPLAY-USAGE](assets/usage.png)

### Features

A. This tool accepts the following types of metadata as input:

    - **Splunk detection names**
    - **MITRE ATT&CK tactic and technique IDs**
    - **Splunk detection GUIDs**
    - **Analytic stories**

It then uses these inputs to identify and replay the attack data associated with them.

B. For automation, you can also provide a simple .txt file.
For example:

**test.txt**:

```
wsreset_uac_bypass.yml
wscript_or_cscript_suspicious_child_process.yml
windows_user_deletion_via_net.yml
Windows User Disabled Via Net
Windows Chromium Browser No Security Sandbox Process
004e32e2-146d-11ec-a83f-acde48001122
01d29b48-ff6f-11eb-b81e-acde48001123
#T1014
T1589.001
Amos Stealer
PromptLock
f64579c0-203f-11ec-abcc-acde48001122
004e32e2-146d-11ec-a83f-acde48001122
```

This file can contain any mix of Security Content metadata you want to replay.
From there, you can choose whether to replay only detection GUIDs, only analytic stories, or all entries using the tool’s greedy replay feature.

C. TOTAL-REPLAY downloads the required Attack Data each time you execute or replay data during detection testing or development. To help reduce disk space usage, the tool generates a cached .yml file for every downloaded dataset. You can then use the `local_data_path` parameter to replay the cached data, allowing you to avoid downloading the same Attack Data again.

## Author

* [Teoderick Contreras](https://www.linkedin.com/in/teoderickc/)

## License

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.