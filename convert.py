import yaml
import os
import sys
import requests
import base64
from utils import SingleQuoted, setup_cmd_args, read_config, get_cron
import boto3

args = setup_cmd_args()
repo = os.environ['repository']
pat = os.environ['pat']
url = f"https://api.github.com/repos/{repo}/contents/{args['database']}.ini"

response = requests.get(
    url = url,
    verify = False,
    headers = {
        "X-GitHub-Api-Version": "2022-11-28",
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}"
    }
).json()

content = base64.b64decode(response['content'])
config = read_config(content)

SCRIPT_DIR = os.path.dirname(__file__) #<-- absolute dir the script is in
COMMIT_WORKFLOW_DIR_PATH = ".github/workflows"
SECTION = f"{args['database']}.{args['operation']}"
BASE_WORKFLOW_DIR_PATH = f"templates/{args['database']}" #"templates/dynamodb"
NEW_FILE_NAME = f"{config[SECTION]['Environment']}.{config[SECTION]['TableNameForBackup']}.{args['operation']}.yaml"


def read_base_workflow():   
    abs_read_file_path = os.path.join(SCRIPT_DIR, f"{BASE_WORKFLOW_DIR_PATH}/{args['operation']}.yaml")
    
    with open(abs_read_file_path, 'r') as file:
        workflow_json = yaml.safe_load(file)
        workflow_json["name"] = NEW_FILE_NAME

        if "env" not in workflow_json:
            workflow_json["env"] = {}
        workflow_json["env"]["workflow_file_name"] = NEW_FILE_NAME

        # if workflow_json["on"]["workflow_dispatch"] is None:
        #     workflow_json["on"]["workflow_dispatch"] = {}

        if "schedule" not in workflow_json["on"]:
            workflow_json["on"]["schedule"] = {}
    
    for key in config[SECTION]:
        print(' {} = {}'.format(key,config[SECTION][key]))
        workflow_json["env"][key] = config[SECTION][key]
    
    return workflow_json


def get_dynamodb_backup_arns(table_name):
    client = boto3.client("dynamodb", region_name=config[SECTION]['RegionName'])
    backup_arns = ["arn1", "arn2", "arn3"]
    
    # response = client.list_backups(
    #     TableName = table_name
    # )

    # for summary in response["BackupSummaries"]:
    #     backup_arns.append(summary["BackupArn"])

    return backup_arns


def write_new_workflow_file(workflow_json):
    abs_write_file_path = os.path.join(SCRIPT_DIR, f"{COMMIT_WORKFLOW_DIR_PATH}/{NEW_FILE_NAME}")
    
    # write to file
    with open(abs_write_file_path, 'w') as file:
        yaml.dump(workflow_json, file, sort_keys=False)
    
    # setup github actions output
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f"workflow_file_name={NEW_FILE_NAME}", file=fh)


workflow_json = read_base_workflow()
if args['operation'] == 'backup':
    workflow_json["on"]["schedule"] = [{"cron": SingleQuoted(get_cron(config[SECTION]["BackupFrequency"])) }]

if args['operation'] == 'restore':
    workflow_json["on"]["schedule"] = [{"cron": SingleQuoted(get_cron(config[SECTION]["RestoreFrequency"])) }]
    
    if config[SECTION]["DynamodbRestoreMethod"] == 'Pitrdate':
        workflow_json["on"]["workflow_dispatch"] = {
            "inputs": {
                "pitr_backup_date": {
                    "type": "string",
                    "required": True
                }
            }
        }

    if config[SECTION]["DynamodbRestoreMethod"] == 'Manual':
        workflow_json["on"]["workflow_dispatch"] = {
            "inputs": {
                "backup_arn": {
                    "type": "choice",
                    "required": True,
                    "options": get_dynamodb_backup_arns(config[SECTION]["TableNameForBackup"])
                }
            }
        }
    
    if int(config[SECTION]["RestoredTableRetentionDays"]) < 0 or int(config[SECTION]["RestoredTableRetentionDays"]) > 7:
        print("RestoredTableRetentionDays can only be between 0 and 7. Please provide a valid value.")
        sys.exit(1)




#print(workflow_json)
write_new_workflow_file(workflow_json)
