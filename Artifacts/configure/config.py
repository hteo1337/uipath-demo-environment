
__author__ = "Andrei"
__version__ = "0.0.1"

from pymongo import MongoClient
import subprocess
import argparse
import json
import os
import os.path
import time
import shutil

from msrestazure.azure_active_directory import MSIAuthentication
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.keyvault.secrets import SecretClient

import orch_setup 


local_config_path = 'c:\\UiPath\\config\\dsf.json'
temp_config_path = 'c:\\Temp\\configFiles'

def get_secret(key_vault, key_name):
    # Create MSI Authentication
    credential = MSIAuthentication()
    client = SecretClient(vault_url=key_vault, credential=credential)
    
    secret_bundle = client.get_secret(key_name)
    secret = secret_bundle.value
    return secret


def get_local_config(path):
    if os.path.exists(path):
        with open(path) as json_file:
            data = json.load(json_file)
        return data
    else:
        return dict()

def write_local_config(path, data):
    with open(path, 'w') as json_file:
        json.dump(data, json_file)

def get_config(mongoUri, config_id):
    client = MongoClient(mongoUri)
    col = client.demoVmConfig['config']

    return col.find_one({"id": config_id})['configuration']

def main(args):
    # read/write local config
    local_config = get_local_config(local_config_path)
    
    # start robot service
    
    os.system("sc.exe start UiRobotSvc")
    time.sleep(15)

    # translate arguments
    if args.autoarm:
        autoarm_list = args.autoarm.split(",")
    else:
        autoarm_list = []
    if args.conn_string:
        # fetch config and connect robot
        conn_string = args.conn_string
    else:
        conn_string = get_secret(args.key_vault, 'mongo-db-conn-string')

    config = get_config(conn_string, args.config_id)
    orch = orch_setup.CloudOrchHelper(args.username, config['authUrl'], config['clientId'],
                                     config['refreshToken'], config['orchUrl'], config['serviceLogicalName'], config['serviceName'], config['accountName'])

    local_config['FolderName'] = orch.folder_name
    local_config['OrganizationUnitID'] = orch.organization_unit_id
    local_config['UniqueUser'] = orch.sap_user_name
    local_config['MSAccount'] = args.ms_account_user
    write_local_config(local_config_path, local_config)

    orch_setup.setup_dsf_folder(
        orch, args.password, args.ms_account_user, args.ms_account_pw, config['processes'], autoarm_list, config['assets'], config['roles'])




if __name__ == '__main__':
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(description="Configure UiPath Robot")

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-u", "--username", action="store", dest="username")
    parser.add_argument("-p", "--password", action="store", dest="password")
    parser.add_argument("--ms_account_user", action="store", dest="ms_account_user")
    parser.add_argument("--ms_account_pw", action="store", dest="ms_account_pw")
    parser.add_argument("--autoarm", action="store", dest="autoarm")
    parser.add_argument("--conn_string", action="store", dest="conn_string")
    parser.add_argument("--key_vault", action="store", dest="key_vault")
    parser.add_argument("--config_id", action="store", dest="config_id", default="presales-demo")

    args = parser.parse_args()
    main(args)


