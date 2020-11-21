import json
from datetime import datetime
from datetime import timedelta 
import fileinput



f = open("aws_cloudtrail_events.json", "r")
now = datetime.now()
now = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
now = datetime.strptime(now,"%Y-%m-%dT%H:%M:%S.%fZ")

for x in f:
    d = json.loads(x)
    latest_event  = datetime.strptime(d["eventTime"],"%Y-%m-%dT%H:%M:%S.%fZ")
difference = now - latest_event
f.close()
for line in fileinput.input("aws_cloudtrail_events.json", inplace=True):

    d = json.loads(line)
    original_time = datetime.strptime(d["eventTime"],"%Y-%m-%dT%H:%M:%S.%fZ")
    new_time = (difference + original_time)

    original_time = original_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    new_time = new_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    print (line.replace(original_time, new_time),end ='')

