import yaml
import json
import configparser
import string
import random
import os
import time
import sys
import argparse

config = configparser.ConfigParser()
config.read('dynamodb.ini')
parser = argparse.ArgumentParser()
script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
workflow_dir_path = ".github/workflows"

def setup_cmd_args():
    parser.add_argument("-o", "--operation", required=True,  help="valid values are 'backup' or 'restore' ")
    parser.add_argument("-t", "--type", required=True, help="valid values are 'ondemand' or 'scheduled' ")
    return vars(parser.parse_args())

def read_and_update_workflow():   
    abs_read_file_path = os.path.join(script_dir, f"{workflow_dir_path}/workflow.yaml")
    
    with open(abs_read_file_path, 'r') as file:
        workflow_json = yaml.safe_load(file)
        workflow_json["on"] = "workflow_dispatch"
        workflow_json["env"]["workflow_file_name"] = file_name
        workflow_json["name"] = file_name
    
    for key in config[section]:
        print(' {} = {}'.format(key,config[section][key]))
        workflow_json["env"][key] = config[section][key]
    return workflow_json

def write_new_workflow_file(workflow_json):
    abs_write_file_path = os.path.join(script_dir, f"{workflow_dir_path}/{file_name}")
    
    with open(abs_write_file_path, 'w') as file:
        yaml.dump(workflow_json, file, sort_keys=False)


args = setup_cmd_args()
if args["operation"].lower() not in ["backup", "restore"]:
    print("Invalid operation. Valid operations are 'backup' or 'restore'. ")
    sys.exit(1)

if args["type"].lower() not in ["ondemand", "scheduled"]:
    print("Invalid type. Valid types are 'ondemand' or 'scheduled'. ")
    sys.exit(1)

random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
section = f"dynamodb.{args['operation'].lower()}.{args['type'].lower()}"
file_name = f"{section}-{random_string}.yaml"
workflow_json = read_and_update_workflow()
write_new_workflow_file(workflow_json)
