import getpass
import json
import keyring
import requests

base_url = "https://kanka.io/api/1.0/"


def get_headers():
    api_token = keyring.get_password('kanka', getpass.getuser())
    header = {
        "Authorization": "Bearer " + api_token,
        "Accept": "application/json"
    }
    return header


def get_url(endpoint):
    return base_url + endpoint


def get_campaigns():
    res = requests.get(get_url('campaigns'), headers=get_headers())
    if res.status_code != 200:
        raise Exception(res.status_code)
    return json.loads(res.content)['data']
