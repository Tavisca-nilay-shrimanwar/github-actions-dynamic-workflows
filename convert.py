import yaml
import os
import sys
import requests
import base64
from utils import SingleQuoted, setup_cmd_args, read_config, get_cron
import boto3

url = f"https://api.github.com/repos/{os.environ['repository']}/contents/dynamodb.ini"
response = requests.get(
    url = url,
    verify = False,
    headers = {
        "X-GitHub-Api-Version": "2022-11-28",
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['pat']}"
    }
).json()

content = base64.b64decode(response['content'])
config = read_config(content)

script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
commit_workflow_dir_path = ".github/workflows"
args = setup_cmd_args()
section = f"{args['database']}.{args['operation']}"
base_workflow_dir_path = f"templates/{args['database']}" #".github/workflows"
new_file_name = f"{config[section]['Environment']}.{config[section]['TableNameForBackup']}.{args['operation']}.yaml"


def read_base_workflow():   
    abs_read_file_path = os.path.join(script_dir, f"{base_workflow_dir_path}/{args['operation']}.yaml")
    
    with open(abs_read_file_path, 'r') as file:
        workflow_json = yaml.safe_load(file)
        workflow_json["name"] = new_file_name

        if "env" not in workflow_json:
            workflow_json["env"] = {}
        workflow_json["env"]["workflow_file_name"] = new_file_name

        # if workflow_json["on"]["workflow_dispatch"] is None:
        #     workflow_json["on"]["workflow_dispatch"] = {}

        if "schedule" not in workflow_json["on"]:
            workflow_json["on"]["schedule"] = {}
    
    for key in config[section]:
        print(' {} = {}'.format(key,config[section][key]))
        workflow_json["env"][key] = config[section][key]
    
    return workflow_json


def get_dynamodb_backup_arns(table_name):
    client = boto3.client("dynamodb", region=config[section]['RegionName'])
    backup_arns = ["arn1", "arn2", "arn3"]
    
    # response = client.list_backups(
    #     TableName = table_name
    # )

    # for summary in response["BackupSummaries"]:
    #     backup_arns.append(summary["BackupArn"])

    return backup_arns


def write_new_workflow_file(workflow_json):
    abs_write_file_path = os.path.join(script_dir, f"{commit_workflow_dir_path}/{new_file_name}")
    
    # write to file
    with open(abs_write_file_path, 'w') as file:
        yaml.dump(workflow_json, file, sort_keys=False)
    
    # setup github actions output
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f"workflow_file_name={new_file_name}", file=fh)


workflow_json = read_base_workflow()
if args['operation'] == 'backup':
    workflow_json["on"]["schedule"] = [{"cron": SingleQuoted(get_cron(config[section]["BackupFrequency"])) }]

if args['operation'] == 'restore':
    workflow_json["on"]["schedule"] = [{"cron": SingleQuoted(get_cron(config[section]["RestoreFrequency"])) }]
    
    if config[section]["DynamodbRestoreMethod"] == 'Pitrdate':
        workflow_json["on"]["workflow_dispatch"] = {
            "inputs": {
                "pitr_backup_date": {
                    "type": "string",
                    "required": True
                }
            }
        }

    if config[section]["DynamodbRestoreMethod"] == 'Manual':
        workflow_json["on"]["workflow_dispatch"] = {
            "inputs": {
                "backup_arn": {
                    "type": "choice",
                    "required": True,
                    "options": get_dynamodb_backup_arns(config[section]["TableNameForBackup"])
                }
            }
        }
    
    # if config[section]["RestoredTableRetentionDays"] < 0 or config[section]["RestoredTableRetentionDays"] > 7:
    #     print("The input restored_table_retention_days can only be between 0 and 7. Invalid input provided.")
    #     sys.exit(1)




#print(workflow_json)
write_new_workflow_file(workflow_json)
