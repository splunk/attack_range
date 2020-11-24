import json
from datetime import datetime
from datetime import timedelta
import fileinput
import os


def manipulate_timestamp(file_path, logger, sourcetype, source):

    if sourcetype == 'aws:cloudtrail':
        manipulate_timestamp_cloudtrail(file_path, logger)



def manipulate_timestamp_cloudtrail(file_path, logger):
    logger.info('Updating timestamps in attack_data before replaying')

    path =  os.path.join(os.path.dirname(__file__), '../attack_data/' + file_path)
    path =  path.replace('modules/../','')

    f = open(path, "r")
    now = datetime.now()
    now = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    now = datetime.strptime(now,"%Y-%m-%dT%H:%M:%S.%fZ")


    first_line = f.readline()
    d = json.loads(first_line)
    latest_event  = datetime.strptime(d["eventTime"],"%Y-%m-%dT%H:%M:%S.%fZ")
    difference = now - latest_event
    f.close()

    for line in fileinput.input(path, inplace=True):

        d = json.loads(line)
        original_time = datetime.strptime(d["eventTime"],"%Y-%m-%dT%H:%M:%S.%fZ")
        new_time = (difference + original_time)

        original_time = original_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        new_time = new_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        print (line.replace(original_time, new_time),end ='')
