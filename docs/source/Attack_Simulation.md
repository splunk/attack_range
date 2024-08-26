# Attack Simulation
The Attack Range supports multiple attack simulation engines.

## Atomic Red Team
Atomic Red Team is a library of tests mapped to the Mitre ATT&CK framework.  
It can be executed with the following command:
```bash
python attack_range.py simulate -e ART -te T1003.001 -t ar-win-ar-ar-0
```
This will execute all atomics for a given ATT&CK technique on the given target. The target need to match the name given from the `python attack_range.py show` command.

## Purple Sharp
[PurpleSharp](https://github.com/mvelazc0/PurpleSharp) is an open source adversary simulation tool written in C# that executes adversary techniques within Windows Active Directory environments. 

It can be executed with the following command to specify a technique:
```bash
python attack_range.py simulate -e PurpleSharp -te T1003.001 -t ar-win-ar-ar-0
```
or you can execute a given playbook:
```bash
python attack_range.py simulate -e PurpleSharp -t ar-win-ar-ar-0 -p configs/purplesharp_playbook_T1003.pb
```

## Kali Linux
[Kali Linux](https://www.kali.org/) is an open-source Debian-based Linux distribution geared towards various information security tasks such as Penetration Testing, Security Research, Computer Forensics, and Reverse Engineering. Attack Range AWS and local is able to build a Kali Linux instance. 
