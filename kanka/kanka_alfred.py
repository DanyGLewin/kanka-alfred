import datetime
import dateutil.parser
import json
import os
import sys
import threading
import traceback
import unicodedata

from fuzzywuzzy import process
import getpass
import keyring
import requests

path = os.getenv("workflow_path")
# path = "/Users/danylewin/dev/kanka-alfred/kanka"
cache_path = path + "/cache.json"
cache_limit = os.getenv("cache_limit")
# cache_limit = "24"
token = os.getenv("token")
json_cache_time_key = "cache_time"

api_url = "https://kanka.io/api/1.0/campaigns/{id}/{endpoint}"
entity_url = "https://kanka.io/en/campaign/{game}/{endpoint}/{entity}"
category_url = "https://kanka.io/en/campaign/{game}/{endpoint}"
campaign_url = "https://kanka.io/en/campaign/{game}"

endpoints = [
    "calendars",
    "conversations",
    "characters",
    "dice_rolls",
    "events",
    "families",
    "items",
    "journals",
    "locations",
    "notes",
    "organisations",
    "quests",
    "races",
    "tags"
]


def get_headers():
    # api_token = keyring.get_password('kanka', getpass.getuser())
    api_token = os.getenv("token")
    header = {
        "Authorization": "Bearer " + api_token,
        "Accept": "application/json"
    }
    return header


def request_campaigns():
    res = requests.get('https://kanka.io/api/1.0/campaigns', headers=get_headers())
    if res.status_code != 200:
        raise Exception(res.status_code)
    data = json.loads(res.content)['data']
    games = {}
    for game in data:
        pretty_name = unicodedata.normalize("NFKD", game["name"]).title()
        games[pretty_name] = game["id"]
    return games


def get_campaigns():
    games = {}
    try:
        with open(cache_path, "r+") as cache:
            cache_data = json.load(cache)["data"].items()
            dashboards = {url: item_name for item_name, url in cache_data if "Dashboard" in item_name}
            for url in dashboards:
                name = dashboards[url].replace(" Dashboard", "")
                game_id = url.split('/')[-1]
                games[name] = game_id
        return games

    except FileNotFoundError:
        return request_campaigns()


class CampaignThread(threading.Thread):
    def __init__(self, campaign_name, campaign_id, out):
        super().__init__()
        self.campaign_name = campaign_name
        self.campaign_id = campaign_id
        self.out = out

    def run(self):
        print(self.campaign_id)
        header = get_headers()
        for endpoint in endpoints:
            request_url = api_url.format(id=self.campaign_id, endpoint=endpoint)
            res = requests.get(request_url, headers=header)
            if res.status_code != 200:
                continue
            response_data = json.loads(res.content)
            for entity in response_data["data"]:
                url = entity_url.format(game=self.campaign_id, endpoint=endpoint, entity=entity["id"])
                # self.out[entity["name"]] = url
                pretty_name = unicodedata.normalize("NFKD", entity["name"]).title()
                self.out[pretty_name] = url

            pretty_endpoint = self.campaign_name + ' ' + endpoint.title()
            self.out[pretty_endpoint] = category_url.format(game=self.campaign_id, endpoint=endpoint)
        pretty_dashboard = self.campaign_name + ' Dashboard'
        self.out[pretty_dashboard] = campaign_url.format(game=self.campaign_id)

        print("Finished ", self.campaign_id)
        return self.out


def get_all_entities():
    data = {}
    all_games = get_campaigns()
    threads = []
    outputs = []

    for (game, game_id) in all_games.items():
        # data.update(get_campaign_entities(game_id))
        outputs.append({})
        threads.append(CampaignThread(game, game_id, outputs[-1]))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    for output_dict in outputs:
        data.update(output_dict)

    data = {
        json_cache_time_key: datetime.datetime.now().isoformat(),
        "data": data
    }

    with open(cache_path, "w+") as cache:
        cache.write(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


def cached_recently(last_cached):
    if not last_cached:
        return False
    now = datetime.datetime.now()
    sync_time = dateutil.parser.parse(last_cached)
    some_hours_ago = now - datetime.timedelta(hours=int(cache_limit))
    return some_hours_ago < sync_time < now


def need_to_cache():
    try:
        with open(cache_path, 'r') as cache:
            cached_data = json.load(cache)
        if json_cache_time_key in cached_data.keys():
            return not cached_recently(cached_data[json_cache_time_key])
    except FileNotFoundError:
        return True
    return False


def load_entities():
    with open(cache_path) as cache:
        return json.load(cache)["data"]


def match_query(query, entities):
    matched_entities = process.extract(query, entities.keys(), limit=25)
    return matched_entities


def alfred_output(matches, entities):
    out = {"items": []}
    for (entity, _) in matches:
        item = {
            'uid': entity,
            'title': entity,
            'subtitle': entities[entity],
            "icon": {
                "path": ""
            },
            "arg": entities[entity],
            "autocomplete": entity
        }
        out['items'].append(item)
    print(json.dumps(out))


def main(query):
    if need_to_cache():
        get_all_entities()
    entities = load_entities()
    matches = match_query(query, entities)
    alfred_output(matches, entities)


def fail(error=None):
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


if len(sys.argv) > 1:
    query = ' '.join(sys.argv[1:])
    try:
        main(query)
    except Exception as e:
        fail(e)

# def old_get_all_entities():
#     data = {}
#     all_games = get_campaigns()
#     for (game, game_id) in all_games.items():
#         print(game)
#         data.update(get_campaign_entities(game_id))
#     return data
#
# def timer(f, *args, **kwargs):
#     import time
#     start = time.time()
#     f(*args, **kwargs)
#     return time.time() - start
