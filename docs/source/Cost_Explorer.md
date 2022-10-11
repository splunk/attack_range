# Cost Explorer
It is a difficult exercise to estimate the cost of any running infrastructure for the attack_range running because each user will use it differently. For our cost estimate we will mimic our experience and how we leverage the attack_range here at Splunk and what our rough costs are. 

Typically each researcher in the Splunk research team will use the attack_range sporadically throughout the week when testing new develop detection's. Testing and developing new detection's is usually an iterative process and it typically involves running multiple attack simulations against the same range and evaluating the data generated. Typically we see this workflow take `3 hours~` on average per detection, and the typical attack_range configuration is:

1 - splunk server

1 - phantom or kali linux machine

and 

1 - Windows Domain Controller

1 - Windows Client

which gets us to `~2 linux machines and ~2 windows machines`. 

## AWS
To calculate the cost depending on your usage, you can use the AWS Cost Explorer:
https://calculator.aws/#/

## Azure
To calculate the cost depending on your usage, you can use the Azure Pricing Calculator:
https://azure.microsoft.com/en-us/pricing/calculator/ 