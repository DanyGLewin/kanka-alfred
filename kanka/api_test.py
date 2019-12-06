import datetime
import getpass
import json
import keyring
import requests

cache_file_name = 'cache.json'
campaign_id = '888'
base_url = "https://kanka.io/api/1.0/campaigns/{id}/".format(id=campaign_id)

endpoints = [
    'characters',
    'locations',
    'organisations',
    'items',
    'notes',
    'events',
    'journals',
    'tags'
]


def udpate_cache():
    now = datetime.datetime.now().isoformat()
    data = {"lastSync": now}
    for endpoint in endpoints:
        print(endpoint)
        data[endpoint] = get_entities(endpoint)
    with open(cache_file_name, 'w+') as cache:
        cache.write(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


def get_headers():
    api_token = keyring.get_password('kanka', getpass.getuser())
    header = {
        "Authorization": "Bearer " + api_token,
        "Accept": "application/json"
    }
    return header


def get_url(endpoint):
    return base_url + endpoint


def get_entities(endpoint, pass_time=False):
    assert endpoint in endpoints
    url = get_url(endpoint)
    headers = get_headers()
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(res.status_code)
    return json.loads(res.content)['data']


def get_campaigns():
    # have a different url, in that they don't include any id
    res = requests.get('https://kanka.io/api/1.0/campaigns', headers=get_headers())
    if res.status_code != 200:
        raise Exception(res.status_code)
    return json.loads(res.content)['data']


def get_characters():
    data = get_entities('characters')
    return data
