
import os
import requests
import json
import psutil
import shutil
import time
import subprocess
import warnings
import base64
import sys

from argparse import ArgumentParser
try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning  # noqa
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # noqa
except ImportError:
    pass


DECORATED_LOG_MSG = "======================== {0} ========================"


def scs_bearer_token(client_id, client_secret, api_version='v2beta1', environment=None):
    scs_token_uri = "{base_uri}/token".format(base_uri=get_scs_base_uri(environment),
                                                                            api_version=api_version)
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(scs_token_uri, data=payload, verify=False)
    print("status code: {0}, response: {1}".format(response.status_code, response.content))
    assert response.status_code in [200]
    content = json.loads(response.content)
    return content['access_token']


def get_scs_base_uri(environment=None):

    prod_base_uri= "https://auth.scp.splunk.com"
    dev_base_uri= "https://auth.{environment}.scp.splunk.com"

    if environment in ['playground', 'staging']:
        return dev_base_uri.format(environment=environment)
    else:
        return prod_base_uri


def get_scs_app_base_uri(environment=None):

    prod_base_uri= "https://app.scp.splunk.com"
    dev_base_uri= "https://app.{environment}.scp.splunk.com"

    if environment in ['playground', 'staging']:
        return dev_base_uri.format(environment=environment)
    else:
        return prod_base_uri

# python ./proxy_setup.py --splunk_home /opt/splunk --environment production --client_id  0oa63qv1xrtH8ITDP2p7  --client_secret VrlRy5g72faYjLarXseSyAmOqyvp3gzFZ8LRUNaP --tenant mcdemo

class ProxyTestArgParse:
    def __init__(self):
        self.arg_options = ArgumentParser()
        self.arg_options.add_argument("--splunk_home", "-splunk_home", dest="splunk_home")
        self.arg_options.add_argument("--environment", "-environment", dest="environment")
        self.arg_options.add_argument("--client_id", "-client_id", dest="client_id")
        self.arg_options.add_argument("--client_secret", "-client_secret", dest="client_secret")
        self.arg_options.add_argument("--tenant", "-tenant", dest="tenant")

    def parse_es_test_args(self):
        return self.arg_options.parse_args()


class ConfigureProxy:

    def __init__(self,
                 splunk_home=None,
                 environment=None,
                 tenant=None,
                 client_id=None,
                 client_secret=None
                 ):

        self.splunk_home = splunk_home

        # required uri's
        self.splunk_base_uri = "https://localhost:8089"
        self.server_info_uri = '/services/server/info?output_mode=json'
        self.headers = {'Content-Type': 'application/json'}
        self.form_urlencoded = {'Content-Type': 'application/x-www-form-urlencoded'}
        self.auth = ('admin', 'Chang3d!')
        self.environment = environment
        self.tenant = tenant
        self.mc_users_pwd = "password"
        self.client_id = client_id
        self.client_secret = client_secret
        self.scp_app_base_uri = get_scs_app_base_uri(environment)
        self.proxy_id = self.get_proxy_id()
        self.scp_auth_token = scs_bearer_token(client_id=self.client_id, client_secret=self.client_secret,
                                               environment=self.environment)

    # New proxy handshake
    def new_proxy_setup(self):
        self.cleanup_stale()

        if self.environment in ['playground', 'staging']:
            self.config_space_bridge()

        self.mod_cert_validation()
        mc_code = self.initialize_tenant_proxy_setup(tenant=self.tenant, auth_token=self.scp_auth_token)
        deployment_id = mc_code.split(':')[1]
        auth_code = self.get_auth_code(mc_code=mc_code, deployment_id=deployment_id)
        deployment_id = self.register_proxy_with_tenant(tenant=self.tenant, auth_token=self.scp_auth_token, auth_code=auth_code, mc_code=mc_code)
        self.time_delay(3)
        self.is_proxy_registration_successful(tenant=self.tenant, deployment_id=deployment_id, auth_token=self.scp_auth_token)
        self.rm_proxy_info_from_mc_from_prev_nightly_run(tenant=self.tenant)
        self.name_the_proxy(tenant=self.tenant, deployment_id=deployment_id)

    def cleanup_stale(self):
        print(DECORATED_LOG_MSG.format("killing splunk_proxyd process"))
        PROC_NAME = "splunk_proxyd"

        for proc in psutil.process_iter():
            # check whether the process to kill name matches
            if proc.name() == PROC_NAME:
                try:
                    print(DECORATED_LOG_MSG.format(proc))
                    proc.kill()
                    time.sleep(30)
                    print(DECORATED_LOG_MSG.format("process killed"))
                    break
                except Exception as e:
                    print('cant kill')

        for proc in psutil.process_iter():
            if proc.name() == PROC_NAME:
                print(DECORATED_LOG_MSG.format(proc))

    def get_proxy_id(self):

        print(DECORATED_LOG_MSG.format("get proxy id"))
        server_info_uri = "{base_uri}/{server_info}".format(base_uri=self.splunk_base_uri, server_info=self.server_info_uri)

        response = requests.get(server_info_uri, auth=self.auth, verify=False, headers=self.headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))

        assert response.status_code in [201, 200]
        content = json.loads(response.content)
        guid = content['entry'][0]['content']['guid']
        return guid

    def mod_cert_validation(self):

        print(DECORATED_LOG_MSG.format("Disable cert validation"))
        proxy_conf_uri = "{base_uri}/servicesNS/nobody/scsproxy/configs/conf-proxy/{proxy_id}?output_mode=json".format(
            base_uri=self.splunk_base_uri,
            proxy_id=self.proxy_id
        )
        payload = {
            "validate_cert": "false"
        }

        response = requests.post(proxy_conf_uri, data=payload, auth=self.auth, verify=False,
                                 headers=self.form_urlencoded)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]
        print(DECORATED_LOG_MSG.format("Disabled cert validation."))

    def initialize_tenant_proxy_setup(self, tenant, auth_token=None):

        print(DECORATED_LOG_MSG.format("Initialize proxy setup with tenant: " + tenant))
        proxy_init_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/init_proxy_setup".format(
            base_uri=self.scp_app_base_uri,
            tenant=tenant
        )
        payload = {
            "proxy_type": "SPLUNK_ES"
        }
        auth_headers = {"Authorization": "Bearer {0}".format(auth_token), 'Content-Type': 'application/json'}
        response = requests.post(proxy_init_uri, json=payload, verify=False, headers=auth_headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]
        content = json.loads(response.content)
        print(DECORATED_LOG_MSG.format("Proxy setup initialized."))
        return content["mc_code"]

    def get_auth_code(self, mc_code=None, deployment_id=None):
        print(DECORATED_LOG_MSG.format("Get auth code"))

        # update product_management stanza
        self.update_product_configuration(is_shc=False, deployment_id=deployment_id, mc_code=mc_code)

        # call proxy endpoint
        self.config_proxy()

        # create mc_users
        self.create_proxy_users()

        # restart proxyd
        self.restart_proxyd()

        # wait 3 minutes
        self.time_delay(3)

        content = self.poll_collection()

        auth_code = base64.b64encode(content['spacebridge_auth_code'] + ':' + content['proxy_instance_id'])
        print('auth_code: {}'.format(auth_code))
        print(DECORATED_LOG_MSG.format("Auth code retrived"))
        return auth_code

    def register_proxy_with_tenant(self, tenant=None, auth_token=None, auth_code=None, mc_code=None):

        print(DECORATED_LOG_MSG.format("Paring proxy with tenant: " + tenant))
        proxy_init_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/proxy_pairing".format(
            base_uri=self.scp_app_base_uri,
            tenant=tenant
        )
        payload = {
            "auth_code": auth_code,
            "mc_code": mc_code
        }
        auth_headers = {"Authorization": "Bearer {0}".format(auth_token), 'Content-Type': 'application/json'}
        response = requests.post(proxy_init_uri, json=payload, verify=False, headers=auth_headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]
        content = json.loads(response.content)
        print(DECORATED_LOG_MSG.format("Proxy pairing complete."))
        return content["deployment_id"]

    def is_proxy_registration_successful(self, tenant=None, deployment_id=None, auth_token=None):

        print(DECORATED_LOG_MSG.format("Verify proxy registration"))
        proxy_init_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/proxy/{deployment_id}/health".format(
            base_uri=self.scp_app_base_uri,
            tenant=tenant,
            deployment_id=deployment_id
        )
        auth_headers = {"Authorization": "Bearer {0}".format(auth_token), 'Content-Type': 'application/json'}
        response = requests.get(proxy_init_uri, verify=False, headers=auth_headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]
        print(DECORATED_LOG_MSG.format("Proxy pairing complete."))

    def name_the_proxy(self, tenant=None, deployment_id=None):
        auth_token = scs_bearer_token(client_id=self.client_id, client_secret=self.client_secret,
                                               environment=self.environment)
        print(DECORATED_LOG_MSG.format("Naming the proxy {}".format(os.uname()[1])))
        name_proxy_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/proxy/{deployment_id}".format(
            base_uri=self.scp_app_base_uri,
            tenant=tenant,
            deployment_id=deployment_id
        )

        payload = {
            "deployment_name": os.uname()[1]
        }
        auth_headers = {"Authorization": "Bearer {0}".format(auth_token), 'Content-Type': 'application/json'}
        response = requests.post(name_proxy_uri, json=payload, verify=False, headers=auth_headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]
        print(DECORATED_LOG_MSG.format("Proxy naming complete."))

    def rm_proxy_info_from_mc_from_prev_nightly_run(self, tenant=None):
        print(DECORATED_LOG_MSG.format("De-register proxy {}".format(os.uname()[1])))
        auth_token = scs_bearer_token(client_id=self.client_id, client_secret=self.client_secret,
                                      environment=self.environment)
        old_deployment_id_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/proxy?deployment_name={deployment_name}".format(
            base_uri=self.scp_app_base_uri,
            tenant=tenant,
            deployment_name=os.uname()[1]
        )
        auth_headers = {"Authorization": "Bearer {0}".format(auth_token), 'Content-Type': 'application/json'}
        response = requests.get(old_deployment_id_uri, verify=False, headers=auth_headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        if response.status_code in [200]:
            content = json.loads(response.content)
            if len(content["items"]) > 0:
                deployment_id = content["items"][0]["id"]

                name_proxy_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/proxy/{deployment_id}".format(
                    base_uri=self.scp_app_base_uri,
                    tenant=tenant,
                    deployment_id=deployment_id
                )

                auth_headers = {"Authorization": "Bearer {0}".format(auth_token), 'Content-Type': 'application/json'}
                response = requests.delete(name_proxy_uri, verify=False, headers=auth_headers)
                print("status code: {0}, response: {1}".format(response.status_code, response.content))
                print(DECORATED_LOG_MSG.format("Proxy de-registration complete."))
        else:
            print(DECORATED_LOG_MSG.format("There is no proxy with {} name to de register".format(os.uname()[1])))

    def update_product_configuration(self, is_shc=False, deployment_id=None, mc_code=None):

        print(DECORATED_LOG_MSG.format("Updated Product configuration...."))
        product_config_uri = "{base_uri}/services/product_management?output_mode=json".format(
            base_uri=self.splunk_base_uri)
        payload = {
            "accept_agreement": True,
            "is_shc": is_shc,
            "deployment_id": deployment_id,
            "mc_code": mc_code
        }

        response = requests.post(product_config_uri, data=payload, auth=self.auth, verify=False,
                                 headers=self.form_urlencoded)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]
        print(DECORATED_LOG_MSG.format("Completed Product Configuration"))

    def restart_proxyd(self):
        ipc_server_uri = "{base_uri}/services/ipc_server/{action}?output_mode=json"
        start_proxyd_uri = ipc_server_uri.format(base_uri=self.splunk_base_uri, action="start")
        stop_ipc_server_uri = ipc_server_uri.format(action="restart_splunk_proxyd", base_uri=self.splunk_base_uri)
        print(DECORATED_LOG_MSG.format("stopping proxyd...."))

        # stop
        response = requests.post(stop_ipc_server_uri, auth=self.auth, verify=False,
                                 headers=self.form_urlencoded)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200, 204]

        print(DECORATED_LOG_MSG.format("stopped proxyd...."))

        # start
        print(DECORATED_LOG_MSG.format("starting proxyd...."))
        response = requests.post(start_proxyd_uri, auth=self.auth, verify=False,
                                 headers=self.form_urlencoded)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))

        print(DECORATED_LOG_MSG.format("started proxyd...."))

    def poll_collection(self):

        proxy_collection_uri = "{base_uri}/servicesNS/nobody/scsproxy/storage/collections/data/proxy_collection?output_mode=json".format(
            base_uri=self.splunk_base_uri)
        print(DECORATED_LOG_MSG.format("Polling  proxy collection...."))

        # stop
        response = requests.get(proxy_collection_uri, auth=self.auth, verify=False,
                                headers=self.form_urlencoded)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]

        content = json.loads(response.content)
        return content[0]

    def create_proxy_users(self):

        print(DECORATED_LOG_MSG.format("Creating proxy users."))
        payload = {
            "admin_user": {
                "name": "mc_user"
                },
            "query_user": {
                "name": "mc_query"
                }
        }
        proxy_collection_uri = "{base_uri}/services/mc_user?output_mode=json".format(
            base_uri=self.splunk_base_uri)

        # stop
        response = requests.post(proxy_collection_uri, auth=self.auth, verify=False,
                                 headers=self.form_urlencoded, data=json.dumps(payload))

        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]
        print(DECORATED_LOG_MSG.format("Proxy users created."))

    def config_proxy(self):

        proxy_conf_uri = "{base_uri}/services/proxy?output_mode=json".format(
            base_uri=self.splunk_base_uri)
        print(DECORATED_LOG_MSG.format("Calling proxy endpoint"))
        response = requests.post(proxy_conf_uri, auth=self.auth, verify=False,
                                headers=self.form_urlencoded)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]

        print("status code: {0}, response: {1}".format(response.status_code, response.content))

        print(DECORATED_LOG_MSG.format("...."))

    def time_delay(self, minutes):
        time.sleep(minutes * 60)

    def config_space_bridge(self):

        proxy_conf_uri = "{base_uri}/servicesNS/nobody/scsproxy/configs/conf-proxy/proxy_internal_settings?output_mode=json".format(
            base_uri=self.splunk_base_uri)

        payload = {
            "proxy_spacebridge_server_address": "grpc.stage1-cloudgateway.spl.mobi"
        }

        print(DECORATED_LOG_MSG.format("configured space bridge proxy endpoint"))
        response = requests.post(proxy_conf_uri, data=payload, auth=self.auth, verify=False,
                                 headers=self.form_urlencoded)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201, 200]

        print("status code: {0}, response: {1}".format(response.status_code, response.content))

        print(DECORATED_LOG_MSG.format("...."))

    def get_deployment_id(self):

        print(DECORATED_LOG_MSG.format("get deployment id"))
        instance_id = self.proxy_id
        print("instance_id: "+instance_id)

        proxy_request_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/proxy_instance?instance={instance_id}".format(
            base_uri=self.scp_app_base_uri,
            tenant=self.tenant,
            instance_id=instance_id
        )

        auth_headers = {"Authorization": "Bearer {0}".format(self.scp_auth_token), 'Content-Type': 'application/json'}

        response = requests.get(proxy_request_uri, verify=False, headers=auth_headers)
        #print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [200]
        content = json.loads(response.content)
        #print(content)
        deployment_id = content['items'][0]['proxy_id']
        print("deployment_id:" + deployment_id)
        return deployment_id

    def get_event_count_from_mc_proxy(self, search):
        print(DECORATED_LOG_MSG.format("get event count from proxy"))
        proxy_request_uri = "{base_uri}/{tenant}/mcservice/v1alpha1/proxy_request".format(
            base_uri=self.scp_app_base_uri,
            tenant=self.tenant
        )
        deployment_id = self.get_deployment_id()

        payload = {
            "proxy_id": deployment_id,
            "query": "/services/search/jobs?output_mode=json",
            "method": "post",
            "body": "status_buckets=300&adhoc_search_level=smart&earliest_time=-2h&latest_time=now&search=search%20index%3Dnotable%20"+search
        }
        auth_headers = {"Authorization": "Bearer {0}".format(self.scp_auth_token), 'Content-Type': 'application/json'}
        response = requests.post(proxy_request_uri, json=payload, verify=False, headers=auth_headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [201]
        content = json.loads(response.content)
        sid = content["sid"]

        payload = {
            "proxy_id": deployment_id,
            "query": "/services/search/jobs/" + sid + "/summary?histogram=true&output_mode=json",
            "method": "get"
        }
        time.sleep(5)
        response = requests.post(proxy_request_uri, json=payload, verify=False, headers=auth_headers)
        print("status code: {0}, response: {1}".format(response.status_code, response.content))
        assert response.status_code in [200, 204]
        if (response.status_code == 200):
            content = json.loads(response.content)
            event_count = content["event_count"]
        else:
            event_count = 0
        return event_count

    def get_event_count_from_investigation_notable(self, search):
        print(DECORATED_LOG_MSG.format("get event count from investigation_notable"))
        notable_uri = "{base_uri}/{tenant}/imservice/v1alpha1/notable?earliest=-2h&latest=now&search={search}".format(
            base_uri=self.scp_app_base_uri,
            tenant=self.tenant,
            search=search
        )
        auth_headers = {"Authorization": "Bearer {0}".format(self.scp_auth_token), 'Content-Type': 'application/json'}
        response = requests.get(notable_uri, verify=False, headers=auth_headers)
        assert response.status_code in [200]
        content = json.loads(response.content)
        event_count = content["total"]
        return event_count

    def get_notable_event_count_from_splunk(self, query):
        print(DECORATED_LOG_MSG.format("get notable event count from splunk"))
        curlcommand = "curl -u "+self.auth[0]+":"+self.auth[1]+" -k "+self.splunk_base_uri+"/services/search/jobs -d search='search "+query+" earliest=-2h | stats count as Total' -d output_mode=json"

        print("curlcommand is: "+curlcommand)

        process = subprocess.Popen(curlcommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        print("out is: "+out)


        jobid = json.loads(out)['sid']

        print("jobid = "+str(jobid))

        curlcommand = "curl -u "+self.auth[0]+":"+self.auth[1]+" -k "+self.splunk_base_uri+"/services/search/jobs/"+jobid+"/results --get -d output_mode=json"
        print("curlcommand is: "+curlcommand)

        sys.stdout.flush()
        time.sleep(30)

        process = subprocess.Popen(curlcommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(30)
        out, err = process.communicate()
        print("out is: " + out)

        event_count = json.loads(out)['results'][0]['Total']
        print("event count = "+ str(event_count))

        return event_count

    def create_manual_notable(self, datasource):
        curlcommand = "curl -k -u " + self.auth[0] + ":" + self.auth[1] + " -d \"name=" + datasource + "\" -d \"index=notable\" -d \"sourcetype=stash\" " + self.splunk_base_uri + "/services/data/inputs/oneshot"
        print("curlcommand is: "+curlcommand)
        process = subprocess.Popen(curlcommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        #print("out is: " + out)

if __name__ == "__main__":
    print(DECORATED_LOG_MSG.format("Configuring proxy handshake"))
    test_args = ProxyTestArgParse().parse_es_test_args()
    print(test_args.__dict__)
    proxy_conf = ConfigureProxy(
        splunk_home=test_args.splunk_home,
        environment=test_args.environment,
        client_id=test_args.client_id,
        client_secret=test_args.client_secret,
        tenant=test_args.tenant
    )
    proxy_conf.new_proxy_setup()
