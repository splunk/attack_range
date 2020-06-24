import sys
from time import sleep
import splunklib.results as results
import splunklib.client as client
import splunklib.results as results


def test_search(splunk_host, splunk_password, search, pass_condition, detection_name, log):

    try:
        service = client.connect(
            host=splunk_host,
            port=8089,
            username='admin',
            password=splunk_password
        )
    except Exception as e:
        log.error("Unable to connect to Splunk instance: " + str(e))
        return 1, {}


    # search and replace \\ with \\\
    #search = search.replace('\\','\\\\')

    if search.startswith('|'):
        search = search
    else:
        search = 'search ' + search

    kwargs = {"exec_mode": "blocking",
            "dispatch.earliest_time": "-60m",
            "dispatch.latest_time": "now"}

    splunk_search = search + ' ' + pass_condition

    try:
        job = service.jobs.create(splunk_search, **kwargs)
    except Exception as e:
        log.error("Unable to execute detection: " + str(e))
        return 1, {}

    test_results = dict()
    test_results['diskUsage'] = job['diskUsage']
    test_results['performance'] = job['performance']
    test_results['runDuration'] = job['runDuration']
    test_results['detection_name'] = detection_name

    if int(job['resultCount']) != 1:
        log.error("Test failed for detection: " + detection_name)
        return 1, test_results
    else:
        log.info("Test successful for detection: " + detection_name)
        return 0, test_results



def search(splunk_host, splunk_password, search_name, log):

    print('\nexecute savedsearch: ' + search_name + '\n')

    service = client.connect(
        host=splunk_host,
        port=8089,
        username='admin',
        password=splunk_password
    )

    # Retrieve the new search
    mysavedsearch = service.saved_searches[search_name]

    kwargs = {"disabled": False,
            "dispatch.earliest_time": "-60m",
            "dispatch.latest_time": "now"}

    # Enable savedsearch and adapt the scheduling time
    mysavedsearch.update(**kwargs).refresh()

    # Run the saved search
    job = mysavedsearch.dispatch()

    # Create a small delay to allow time for the update between server and client
    sleep(2)

    # Wait for the job to finish--poll for completion and display stats
    while True:
        job.refresh()
        stats = {"isDone": job["isDone"],
                 "doneProgress": float(job["doneProgress"])*100,
                  "scanCount": int(job["scanCount"]),
                  "eventCount": int(job["eventCount"]),
                  "resultCount": int(job["resultCount"])}
        status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                  "%(eventCount)d matched   %(resultCount)d results") % stats

        sys.stdout.write(status)
        sys.stdout.flush()
        if stats["isDone"] == "1":
            break
        sleep(2)

    # Get the results and display them
    for result in results.ResultsReader(job.results()):
        print()
        print(result)

    # disable the savedsearch
    kwargs = {"disabled": True}
    mysavedsearch.update(**kwargs).refresh()



def list_searches(splunk_host, splunk_password):

    service = client.connect(
        host=splunk_host,
        port=8089,
        username='admin',
        password=splunk_password
    )

    # List the saved searches that are available to the current user
    return service.saved_searches
