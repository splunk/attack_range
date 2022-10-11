# Attack Range Docs

```{warning}
The documentation is under development.
```
The Splunk Attack Range is an open-source project maintained by the Splunk Threat Research Team. It builds instrumented cloud and local environments, simulates attacks, and forwards the data into a Splunk instance. This environment can then be used to develop and test the effectiveness of detections.

The Attack Range is a detection development platform, which solves three main challenges in detection engineering:
* The user is able to quickly build a small lab infrastructure as close as possible to a production environment.
* The Attack Range performs attack simulation using different engines such as Atomic Red Team or Caldera in order to generate real attack data. 
* It integrates seamlessly into any Continuous Integration / Continuous Delivery (CI/CD) pipeline to automate the detection rule testing process.  

```{toctree}
:caption: 'Contents:'
:maxdepth: 2

Attack Range AWS <Attack_Range_AWS>
Attack Range Azure <Attack_Range_Azure>
Attack Range Local <Attack_Range_Local>
Attack Range Cloud <Attack_Range_Cloud>
Control Attack Range <Control_Attack_Range>
Attack Range Config <Attack_Range_Config>
Attack Simulation <Attack_Simulation>
Attack Data <Attack_Data>
Attack Range Features <Attack_Range_Features>
Cost Explorer <Cost_Explorer>

```