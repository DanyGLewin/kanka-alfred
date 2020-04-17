import datetime
import dateutil.parser
import json
import os
import sys
import threading
import time
import traceback
import unicodedata

from fuzzywuzzy import process
import requests

# api user token
token = os.getenv("token")

# path where data will be cached and errors logged
cache_path = "cache.json"
log_path = "log.txt"

# number of hours before refreshing cache
cache_limit = os.getenv("cache_limit")

# json key for the timestamp value
json_cache_time_key = "cache_time"

# request url for listing entities
api_url = "https://kanka.io/api/1.0/campaigns/{id}/{endpoint}"

# individual entity url
entity_url = "https://kanka.io/en/campaign/{game}/{endpoint}/{entity}"

# category url
category_url = "https://kanka.io/en/campaign/{game}/{endpoint}"

# dashboard url
campaign_url = "https://kanka.io/en/campaign/{game}"

# list of entity endpoints
endpoints = [
    "abilities",
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
    """
    required headers for api calls
    token is stored as workflow variable
    """
    api_token = os.getenv("token")
    header = {
        "Authorization": "Bearer " + api_token,
        "Accept": "application/json"
    }
    return header


def request_campaigns():
    """
    get campaign names and ids from server
    unicode encoding sometimes gets messed up, so we clean that
    """
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
    """
    if cache exists, find the dashboards in it, extract name and id from the name and url respectively
    if cache doesn't exist, get names and ids from server
    """
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

        return self.out


def get_all_entities():
    """
    get all campaigns and write them to cache.json
    uses a separate thread for each campaign
    """
    data = {}
    all_games = get_campaigns()
    threads = []
    outputs = []

    for (game, game_id) in all_games.items():
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
    """
    whether or not entities have been cached recently
    recently is defined as "in the past X hours", where X = last_cached
    """
    if not last_cached:
        return False
    now = datetime.datetime.now()
    sync_time = dateutil.parser.parse(last_cached)
    some_hours_ago = now - datetime.timedelta(hours=int(cache_limit))
    return some_hours_ago < sync_time < now


def need_to_cache():
    """
    true  if there is no cache or the cache hasn't been updated recently
    """
    try:
        with open(cache_path, 'r') as cache:
            cached_data = json.load(cache)
        if json_cache_time_key in cached_data.keys():
            return not cached_recently(cached_data[json_cache_time_key])
    except FileNotFoundError:
        return True
    return False


def load_entities():
    """
    return {name:url} dictionary from cache, containing all entities in all campaigns
    """
    with open(cache_path) as cache:
        return json.load(cache)["data"]


def match_query(query, entities):
    """
    Find the closest matches to query among the loaded entity names

    Results generally stop being relevant after the first 15-20,
    but leaving it at 25 for good measure. Limit has very little effect on performance at these scales.
    """
    matched_entities = process.extract(query, entities.keys(), limit=25)
    return matched_entities


def alfred_output(matches, entities):
    """
    return the matched entities as alfred action items
    """
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
    """
    get all entities from the server if needed, then return the closest matches to user
    """
    if need_to_cache():
        get_all_entities()
    entities = load_entities()
    matches = match_query(query, entities)
    alfred_output(matches, entities)


def fail(query):
    """
    if something went wrong, write traceback to file and make an action item to open it
    """
    log = open(log_path, "a")
    log.write("""timestamp: {time}
query: {query}
{trace}

""".format(time=time.time(),
           query=query,
           trace=traceback.format_exc()))
    log.close()

    out = {
        "items": [
            {
                'uid': 'whoops',
                'title': 'whoopsie',
                'type': 'file',
                'subtitle': 'Select to open log file',
                'icon': {
                    'path': ''
                },
                'arg': log_path,
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
        fail(query)

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
