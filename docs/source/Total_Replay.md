# TOTAL-REPLAY

## Description

This lightweight tool helps you make the most of Splunk’s [Security Content](https://github.com/splunk/security_content) metadata, such as detection names, analytic stories, and more, by replaying relevant test event logs or attack data from either the [Splunk Attack Data](https://github.com/splunk/attack_data) or [Splunk Attack Range](https://github.com/splunk/attack_range) projects.


## MAC/LINUX:

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
5. if you encounter problem with colorama python library just update it.
```  
poetry update colorama
```

### Windows OS:

We recommend using the Windows Subsystem for Linux (WSL). You can find a tutorial [here](https://learn.microsoft.com/en-us/windows/wsl/install). After installing WSL, you can follow the steps described in the Linux section.


for more information please visit the [Splunk Attack Data Repo](https://github.com/splunk/attack_data/)