import yaml
import argparse
import configparser
import sys

parser = argparse.ArgumentParser()
config = configparser.ConfigParser()
config.optionxform=str

class SingleQuoted(str):
    pass

def represent_single_quoted(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")

yaml.add_representer(SingleQuoted, represent_single_quoted)

def setup_cmd_args():
    parser.add_argument("-o", "--operation", required=True,  help="valid values are 'backup' or 'restore' ")
    parser.add_argument("-d", "--database", required=True)
    return vars(parser.parse_args())

def read_config(content):
    config.read_string(content.decode())
    return config

def get_cron(frequency):
    if frequency == 'daily':
        return '0 4 * * *'

    elif frequency == 'twice-a-day' or frequency == 'twice_a_day':
        return '0 4,16 * * *'

    else: 
        print("Invalid input for frequency.")
        sys.exit(1)
