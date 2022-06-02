
import sys
from time import sleep
import splunklib.results as results
import splunklib.client as client
import splunklib.results as results
import requests



def export_search(host, s, password, export_mode="raw", out=sys.stdout, username="admin", splunk_rest_port=8089):
    """
    Exports events from a search using Splunk REST API to a local file.
    This is faster than performing a search/export from Splunk Python SDK.
    @param host: splunk server address
    @param s: search that matches events
    @param password: Splunk server password
    @param export_mode: default `raw`. `csv`, `xml`, or `json`
    @param out: local file pointer to write the results
    @param username: Splunk server username
    @param port: Splunk server port
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    r = requests.post("https://%s:%d/servicesNS/admin/search/search/jobs/export" % (host, splunk_rest_port),
                      auth=(username, password),
                      data={'output_mode': export_mode,
                            'search': s,
                            'max_count': 1000000},
                      verify=False)
    out.write(r.text.encode('utf-8'))