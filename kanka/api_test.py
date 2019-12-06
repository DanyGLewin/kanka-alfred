import datetime
import dateutil.parser
from fuzzywuzzy import process
import getpass
import json
import keyring
import requests

cache_file_name = 'cache.json'
cached_time_key = 'cached'

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
    if not force:
        with open(cache_file_name, 'r') as cache:
            cached_data = json.load(cache)
        if cached_time_key in cached_data.keys():
            if not need_to_cache(cached_data[cached_time_key]):
                print("No need to update")
                return

    data = {cached_time_key: now.isoformat()}
    for endpoint in endpoints:
        print(endpoint)
        entities = get_entities(endpoint)
        add_entity_urls(endpoint, entities)
        data[endpoint] = entities
    with open(cache_file_name, 'w+') as cache:
        cache.write(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


def need_to_cache(last_cached):
    now = datetime.datetime.now()
    sync_time = dateutil.parser.parse(last_cached)
    two_hours_ago = now - datetime.timedelta(hours=2)
    return not two_hours_ago < sync_time < now


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
    # have a different url, in that they don't include any id
    res = requests.get('https://kanka.io/api/1.0/campaigns', headers=get_headers())
    if res.status_code != 200:
        raise Exception(res.status_code)
    return json.loads(res.content)['data']


def get_characters():
    data = get_entities('characters')
    return data


def load_entities():
    try:
        with open(cache_file_name):
            pass
    except FileNotFoundError:
        return get_all_entities()

    with open(cache_file_name) as cache:
        data = json.load(cache)
        return {entity['name']: entity['url'] for endpoint in endpoints for entity in data[endpoint]}


def get_all_entities():
    # TODO
    pass


def find_entity(query):
    all_entities = load_entities()

    sorted_entity_names = process.extract(query, all_entities, limit=55)
    out = {"items": []}
    for entity_name in sorted_entity_names:
        item = {
            'uid': entity_name[0],
            'title': entity_name[0],
            'subtitle': all_entities[entity_name[0]],
            "icon": {
                "path": "/Users/danylewin/dev/aon_search/Nethys.png"
            },
            "arg": all_entities[entity_name[0]].replace(" ", "%20"),
            "autocomplete": entity_name[0]
        }
        out['items'].append(item)
    print(json.dumps(out))
