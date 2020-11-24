import json
from datetime import datetime
from datetime import timedelta
import fileinput
import os
import re


def manipulate_timestamp(file_path, logger, sourcetype, source):

    logger.info('Updating timestamps in attack_data before replaying')

    if sourcetype == 'aws:cloudtrail':
        manipulate_timestamp_cloudtrail(file_path, logger)

    if source == 'WinEventLog:System' or source == 'WinEventLog:Security':
        manipulate_timestamp_windows_event_log_raw(file_path, logger)


def manipulate_timestamp_windows_event_log_raw(file_path, logger):
    path =  os.path.join(os.path.dirname(__file__), '../attack_data/' + file_path)
    path =  path.replace('modules/../','')

    f = open(path, "r")
    now = datetime.now()
    now = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    now = datetime.strptime(now,"%Y-%m-%dT%H:%M:%S.%fZ")

    # read raw logs
    print('data manipulation')
    data = f.read()
    lst_matches = re.findall(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} AM|PM", data)
    print(lst_matches[-1])
    f.close()

    # to do here
    # 1) get position of match
    # 2) calculate new timestamp
    # 3) replace with re.sub and replacement function https://lzone.de/examples/Python%20re.sub
    

def manipulate_timestamp_cloudtrail(file_path, logger):
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
