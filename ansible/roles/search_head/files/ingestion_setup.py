import os
import shutil
from argparse import ArgumentParser
import requests
import json
import pem
import warnings
import shutil

PLAYGROUND = "playground"
STAGING = "staging"
PRODUCTION = "production"
DECORATED_LOG_MSG = "======================== {0} ========================"

class IngestionArgParse:
    def __init__(self):
        self.arg_options = ArgumentParser()
        self.arg_options.add_argument("--splunk_home", "-splunk_home", dest="splunk_home")
        self.arg_options.add_argument("--tenant", "-tenant", dest="tenant")
        self.arg_options.add_argument("--environment", "-environment", dest="environment")
        self.arg_options.add_argument("--test_client_secret", "-test_client_secret", dest="test_client_secret")
        self.arg_options.add_argument("--test_client_id", "-test_client_id", dest="test_client_id")

    def parse_args(self):
        return self.arg_options.parse_args()


class SetupIngestion(object):
    '''
    Setup ingestion in scsproxy.
    '''
    def __init__(self, splunk_home, tenant, environment, client_id, client_secret):
        self.splunk_home = splunk_home
        self.tenant = tenant
        self.environment = environment
        self.client_id = client_id
        self.client_secret = client_secret
        self.bots_data =""

    def update_outputs_conf(self):
        '''
        Update outputs.conf based on the environment
        '''
        ## Update tcoput stanza:
        settings = {
            "defaultGroup": "noOutputGroup",
            "indexAndForward": "true"
        }

        url = 'https://localhost:8089/servicesNS/{}/{}/configs/conf-{}/{}'.format(
            'nobody',
            'scsproxy',
            'outputs',
            'tcpout')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            r = requests.post(url, data=settings, auth=('admin', 'Chang3d!'), verify=False)
            if r.status_code not in  [200, 201]:
                r.raise_for_status()

        ## Update tcpout:missioncontrol stanza.
        settings = {
            "server": self.get_forwarder_server() + ":9997",
            "useACK": "false",
            "sslCommonNameToCheck": self.get_forwarder_server(),
            "sslVerifyServerCert": "false",
            "clientCert": self.get_client_cert(),
            "sslRootCAPath": self.get_ssl_root_ca_path(),
            "disabled": "false"
        }
#        if self.environment.lower() is PRODUCTION:
#            settings.update({"sslVerifyServerCert": "true"})

        url = 'https://localhost:8089/servicesNS/{}/{}/configs/conf-{}/{}'.format(
            'nobody',
            'scsproxy',
            'outputs',
            'tcpout:missioncontrol')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            r = requests.post(url, data=settings, auth=('admin', 'Chang3d!'), verify=False)
            if r.status_code not in  [200, 201]:
                r.raise_for_status()

    def get_forwarder_server(self):
        '''
        Get the forwarder server based on the
        environment.
        '''
        server = "forwarders.scp.splunk.com"
        server_non_prod = "forwarders.{}.scp.splunk.com"

        if self.environment.lower() == PRODUCTION:
            return server
        return server_non_prod.format(self.environment.lower())

    def get_auth_endpoint(self):
        '''
        Get the endpoint
        '''
        server = "auth{}.scp.splunk.com"

        if self.environment.lower() == PRODUCTION:
            return server.format("")
        return server.format("." + self.environment.lower())

    def get_api_endpoint(self):
        '''
        Get the endpoint
        '''
        server = "api{}.scp.splunk.com"

        if self.environment.lower() == PRODUCTION:
            return server.format("")
        return server.format("." + self.environment.lower())

    def get_client_cert(self):
        """
        Get the path to client cert
        """

        dest_dir =  os.path.join(self.splunk_home, "etc", "apps", "scsproxy", "auth")

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        ## Crete the certificate on the fly!

        ## Step 1: Create self-signed certificate.
        os.system("openssl genrsa -out my_forwarder.key 2048")

        ## Step 2: Create a CSR and sign it with private key from Step 1
        os.system('openssl req -new -key "my_forwarder.key" -out "my_forwarder.csr" -subj "/C=US/ST=CA/O=my_organization/CN=my_forwarder/emailAddress=carlsbad-engineering@splunk.com"')
        os.system('openssl x509 -req -days 730 -in "my_forwarder.csr" -signkey "my_forwarder.key" -out "my_forwarder.pem" -sha256')

        ## Step 3: Upload the key to the tenant
        certs = pem.parse_file("my_forwarder.pem")
        formatted_pem_file =  str(certs[0])

        ## Step 3.1: Get the bearer token.
        endpoint = self.get_auth_endpoint()
        url = "https://" + endpoint + "/token"

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        r = requests.post(
            url,
            data=payload)

        print r.content

        if r.status_code is not 200:
            raise Exception("Could not get bearer token to post certificate")

        content = json.loads(r.content)
        bearer_token = content["access_token"]

        ## Step 3.2: Post the certificate to the tenant
        endpoint = self.get_api_endpoint()

        ###Removed this step## Delete the certificates:
        ##url = "https://" + endpoint + "/" + self.tenant + "/forwarders/v2beta1/certificates/1"
        ##headers = {
        ##    "Authorization": "Bearer {}".format(bearer_token)
        ##}
#########
        ##r = requests.delete(
        ##    url,
        ##    headers=headers,
        ##)
#########
        ##print("Delete cert in slot 0 -> status code: {0}, response: {1}".format(r.status_code, r.content))

        ## Create certificates.
        url = "https://" + endpoint + "/" + self.tenant + "/forwarders/v2beta1/certificates"
        headers = {
            "Authorization": "Bearer {}".format(bearer_token)
        }

        r = requests.post(
            url,
            headers=headers,
            data=json.dumps({
                "pem": formatted_pem_file
            })
        )

        print r.content
        if r.status_code is not 200:
            raise Exception("Could not post certificate")

        ## Step 4: Configure forwarder to use the client certificate.
        os.system("cat my_forwarder.pem my_forwarder.key > my_forwarder-keys.pem")

        ## Move the concatenated file
        dest_dir =  os.path.join(self.splunk_home, "etc", "apps", "scsproxy", "auth")
        shutil.copy("my_forwarder-keys.pem", dest_dir)

        return os.path.join(dest_dir, "my_forwarder-keys.pem")

    def get_ssl_root_ca_path(self):
        """
        Get sslRootCAPath, this will not work
        """
        dir_path = os.path.dirname(os.path.realpath(__file__))
        #src_file = os.path.join(dir_path, "data", "DigiCertGlobalRootCA.pem")
        dest_dir =  os.path.join(self.splunk_home, "etc", "apps", "scsproxy", "auth")

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        #shutil.copy(src_file, dest_dir)

        return os.path.join(dest_dir, "DigiCertGlobalRootCA.pem")

    def reload_outputs_conf(self):

        url = 'https://localhost:8089/services/data/outputs/tcp/group/_reload?output_mode=json'

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            response = requests.get(url, auth=('admin', 'Chang3d!'), verify=False)
            if response.status_code not in  [200, 201]:
                response.raise_for_status()
            print("status code: {0}, response: {1}".format(response.status_code, response.content))

    def enable_savedsearches(self):

        print(DECORATED_LOG_MSG.format("Enable saved searches"))
        savedsearches = [
            'Mission Control - Forward Notable Events',
            'Mission Control - Forward Risk Events',
            'Mission Control - Retry Unacknowledged Events',
            'Mission Control - Forward Sequenced Notable Events',
            'Mission Control - Forward Content Management Data'
            ]

        ## /servicesNS/nobody/SplunkEnterpriseSecuritySuite/saved/searches/Event%20Sequencing%20Engine%20-%20Main
        for savedsearch in savedsearches:
            print(DECORATED_LOG_MSG.format("Enable saved search - {savedsearch}".format(savedsearch=savedsearch)))
            proxy_conf_uri = "https://localhost:8089/servicesNS/nobody/scsproxy/configs/conf-savedsearches/{savedsearch}?output_mode=json".format(
                savedsearch=savedsearch
            )
            payload = {
                "disabled": "false"
            }

            response = requests.post(proxy_conf_uri, data=payload, auth=('admin', 'Chang3d!'), verify=False,
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            print("status code: {0}, response: {1}".format(response.status_code, response.content))
            assert response.status_code in [201, 200]
            print(DECORATED_LOG_MSG.format("Enabled saved search - {savedsearch}".format(savedsearch=savedsearch)))

        ## Enable Event Sequencing Engine Main saved search
        uri = "https://localhost:8089/servicesNS/nobody/SplunkEnterpriseSecuritySuite/saved/searches/Event%20Sequencing%20Engine%20-%20Main"
        payload = {
            "disabled": "false"
        }
        response = requests.post(proxy_conf_uri, data=payload, auth=('admin', 'Chang3d!'), verify=False,
                                    headers={'Content-Type': 'application/x-www-form-urlencoded'})
        assert response.status_code in [201, 200]

        print(DECORATED_LOG_MSG.format("Enabled saved search - Event Sequencing Engine - Main"))

        print(DECORATED_LOG_MSG.format("Enabled saved searches."))

    def setup_bots_data(self):
        '''
        Setup bots data
        https://confluence.splunk.com/display/MG/Setting+up+BOTS+configuration
        '''
        if self.bots_data:
            print(DECORATED_LOG_MSG.format("BOTS data setup"))
            dir_path = os.path.dirname(os.path.realpath(__file__))
            bots_data_dir = os.path.join(dir_path, "bots_mc")
            apps_dir =  os.path.join(self.splunk_home, "etc", "apps")

            ## Step 1: Copy SA-bots app.
            print(DECORATED_LOG_MSG.format("Installing SA-bots app"))
            sa_bots = os.path.join(bots_data_dir, "SA-bots")
            shutil.copytree(sa_bots, os.path.join(apps_dir, "SA-bots"))

            ## Step 2: Copy DA-ESS-ContentUpdate
            print(DECORATED_LOG_MSG.format("Installaing DA-ESS-ContentUpdate app"))
            da_ess_cu = os.path.join(bots_data_dir, "DA-ESS-ContentUpdate")
            shutil.copytree(da_ess_cu, os.path.join(apps_dir, "DA-ESS-ContentUpdate"))

            ## Step 3: Copy bots directory and bots.dat
            print(DECORATED_LOG_MSG.format("Copying bots data"))
            lib_splunk = os.path.join(self.splunk_home, "var", "lib", "splunk")
            shutil.copytree(os.path.join(bots_data_dir, "bots"), os.path.join(lib_splunk, "bots"))
            shutil.copy(os.path.join(bots_data_dir, "bots.dat"), lib_splunk)

            ## Step 4: Ensure that admin role searches across "All non-internal Indexes" or at least "bots" index by default.
            print(DECORATED_LOG_MSG.format("Changing search indexes default"))
            url = "https://localhost:8089/services/authorization/roles/admin"
            payload = {
                "output_mode": "json",
                "srchIndexesDefault":["*", "main"]
            }
            response = requests.post(
                url,
                data=payload,
                auth=('admin', 'Chang3d!'),
                verify=False)

            print("status code: {0}, response: {1}".format(response.status_code, response.content))
            assert response.status_code in [200, 201]


if __name__ == "__main__":
    print "-----Running Ingestion Setup-----"

    test_args = IngestionArgParse().parse_args()

    ingestion = SetupIngestion(
        test_args.splunk_home,
        test_args.tenant,
        test_args.environment,
        test_args.test_client_id,
        test_args.test_client_secret
	)
    ingestion.update_outputs_conf()
    ingestion.reload_outputs_conf()
    ingestion.enable_savedsearches()
    #ingestion.setup_bots_data()
