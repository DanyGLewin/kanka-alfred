import datetime
import dateutil.parser
from fuzzywuzzy import process
import getpass
import json
import keyring
import requests
import sys

import traceback

cache_file_name = '/Users/danylewin/dev/kanka-alfred/kanka/cache.json'
categories_file_name = '/Users/danylewin/dev/kanka-alfred/kanka/categories.json'
cached_time_key = 'cached'
caching_wait_hours = 24

campaign_id = '888'
api_url = "https://kanka.io/api/1.0/campaigns/{id}/".format(id=campaign_id)
entity_url = "https://kanka.io/en/campaign/{id}/".format(id=campaign_id)

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


def udpate_cache(force=False):
    now = datetime.datetime.now()

    data = {cached_time_key: now.isoformat()}
    for endpoint in endpoints:
        entities = get_entities(endpoint)
        add_entity_urls(endpoint, entities)
        data[endpoint] = entities

    with open(cache_file_name, 'w+') as cache:
        cache.write(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


def need_to_cache():
    try:
        with open(cache_file_name, 'r') as cache:
            cached_data = json.load(cache)
        if cached_time_key in cached_data.keys():
            return not cached_recently(cached_data[cached_time_key])
    except FileNotFoundError:
        return True
    return False


def cached_recently(last_cached):
    if not last_cached:
        return False
    now = datetime.datetime.now()
    sync_time = dateutil.parser.parse(last_cached)
    some_hours_ago = now - datetime.timedelta(hours=caching_wait_hours)
    return some_hours_ago < sync_time < now


def add_entity_urls(endpoint, entities):
    for entity in entities:
        entity_id = str(entity['id'])
        url = entity_url + endpoint + '/' + entity_id
        entity['url'] = url


def get_headers():
    api_token = keyring.get_password('kanka', getpass.getuser())
    header = {
        "Authorization": "Bearer " + api_token,
        "Accept": "application/json"
    }
    return header


def get_url(endpoint):
    return api_url + endpoint


def get_entities(endpoint):
    assert endpoint in endpoints
    url = get_url(endpoint)
    headers = get_headers()

    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(res.status_code)
    return json.loads(res.content)['data']


def get_campaigns():
    # have a different url format, they don't include any id
    res = requests.get('https://kanka.io/api/1.0/campaigns', headers=get_headers())
    if res.status_code != 200:
        raise Exception(res.status_code)
    return json.loads(res.content)['data']


def get_characters():
    data = get_entities('characters')
    return data


def load_entities():
    with open(cache_file_name) as cache:
        data = json.load(cache)
    return {entity['name']: entity['url'] for endpoint in endpoints for entity in data[endpoint]}


def load_categories():
    with open(categories_file_name) as categories:
        return json.load(categories)


def find_entity(query):
    if need_to_cache():
        wait()
        udpate_cache(force=False)
        return

    all_entities = load_entities()
    all_entities.update(load_categories())
    sorted_entity_names = process.extract(query, all_entities.keys(), limit=25)
    out = {"items": []}
    for entity_name in sorted_entity_names:
        item = {
            'uid': entity_name[0],
            'title': entity_name[0],
            'subtitle': all_entities[entity_name[0]],
            "icon": {
                "path": ""
            },
            "arg": all_entities[entity_name[0]],
            "autocomplete": entity_name[0]
        }
        out['items'].append(item)
    print(json.dumps(out))


def fail(e=None):
    out = {
        "items": [
            {
                'uid': 'whoops',
                'title': 'whoopsie',
                'subtitle': 'copy this for traceback',
                'icon': {
                    'path': ''
                },
                'arg': str(traceback.format_exc()),
                'autocomplete': 'whoopsie'
            }
        ]
    }
    print(json.dumps(out))


def wait():
    out = {
        "rerun": 1,
        "items": [
            {
                'uid': 'loading...',
                'title': 'loading...',
                'subtitle': 'Loading all entities from campaign',
                'icon': {
                    'path': ''
                },
                'autocomplete': 'loading...',
                'valid': False
            }
        ]
    }
    s = json.dumps(out)
    print(s)


if len(sys.argv) > 1:
    query = ' '.join(sys.argv[1:])
    try:
        find_entity(query)
    except Exception as e:
        fail(e)
