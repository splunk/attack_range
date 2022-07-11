# Attack Simulation
The Attack Range supports multiple attack simulation engines.

## Atomic Red Team
Atomic Red Team is a library of tests mapped to the Mitre ATT&CK framework.  
It can be executed with the following command:
```
python attack_range.py simulate -e ART -te T1003.001 -t ar-win-ar-ar-0
```
This will execute all atomics for a given ATT&CK technique on the given target. The target need to match the name given from the `python attack_range.py show` command.

## Purple Sharp
PurpleSharp is an open source adversary simulation tool written in C# that executes adversary techniques within Windows Active Directory environments.  
It can be executed with the following command to specify a technique:
```
python attack_range.py simulate -e PurpleSharp -te T1003.001 -t ar-win-ar-ar-0
```
or you can execute a given playbook:
```
python attack_range.py simulate -e PurpleSharp -t ar-win-ar-ar-0 -p configs/purplesharp_playbook_T1003
```

## Prelude
Prelude Operator can be automatically configured and deployed with a Splunk Attack Range allowing a user to easily launch attacks via Operator on a running range using the pre-installed Penuma agents. To get started with Prelude follow these simple steps:

1. Install [Prelude Operator](https://www.prelude.org/download) on your local machine
2. Configure an attack range with Prelude (configure the [accountEmail](#Prelude-accountEmail) setting)
3. Build an attack range
4. Add [a manual new redirector](#Add-a-manual-redirector) to Prelude Operator
 
For an overview on how Prelude works inside the attack range see the general architecture below:

![Prelude Attack Range Architecture 3 0](https://user-images.githubusercontent.com/1476868/174927368-210623eb-2165-491e-8e2f-861f2f002fb2.png)

### A few things to note from this architecture:

* A Headless Operator/Redirector is installed on the Splunk server, this means a user **needs**:
1. Operator installed in their local machine (can be downloaded [here](https://www.prelude.org/download)) to connect and manage it, see screenshot below.
2. Or talk through it via the API on TCP port 
* Pneuma is installed and supported on the Windows (server and domain controller) and Linux machines ONLY today
* Pneuma connects back to the Headless Operator/Redirector via TCP port 2323

### Prelude accountEmail

When an Splunk Attack Range is configured it will need to know the auto generated `accountEmail` to connect to. This can be obtained via the Prelude Operator client via clicking on **Connect** ->  **Deploy Manual Redirectors**, see screenshot below for an example.

<img width="1440" alt="image" src="https://user-images.githubusercontent.com/1476868/174924831-9bb9db96-a59e-4090-9ca7-f563ed4af074.png">

Once an Attack Range has successfully been built with Prelude Operator the `show` command will include a token and FQDN like below:

```
Access Prelude Operator UI via:
	redirector FQDN > 18.225.27.90
	Token: fbe9254b-5fb8-44d2-a02c-31e0a10f62c9
```

### Add a manual redirector

This should then be inserted in the **Deploy Manual Redirectors** form on the locally installed Operator, click on `Add` to be able to attack these hosts via Operator. If all worked well you should end up with a list of hosts and a purple "Your are connected" message above  available like the screenshot below.

<img width="1440" alt="image" src="https://user-images.githubusercontent.com/1476868/174928203-d51fb6d5-7637-479e-b3bb-b4c5cba11767.png">

## Kali Linux
Kali Linux is an open-source Debian-based Linux distribution geared towards various information security tasks such as Penetration Testing, Security Research, Computer Forensics, and Reverse Engineering. Attack Range AWS and local is able to build a Kali Linux instance. 