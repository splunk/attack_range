# Cost Explorer
It is challenging to estimate the cost of all running Attack Range infrastructure because each person will use it differently. In our cost estimate, we will mimic our experience, how we leverage the attack_range here at Splunk, and our rough costs.

Typically, each researcher in the Splunk research team will use the Attack Range sporadically throughout the week when developing and testing new detections. Creating and testing new detections is usually an iterative process that involves running multiple attack simulations against the same range and evaluating the data generated. Typically, we see this workflow take `3 hours~` on average per detection, and the typical Attack Range configuration is:

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
