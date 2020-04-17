# Kanka-alfred
Alfred 4 workflow for browsing Kanka campaigns

## Requirements
To use this Workflow you must have Alfred, and own a Powerpack license.
This Workflow works on OSX 10.15 Catalina, and should work on any mac version if you have python 3.7 installed.

## Installation & Setup
Download and run `Kanka-alfred-1.0.alfredworkflow`.

Once installed, go to [https://kanka.io/en/settings/api](https://kanka.io/en/settings/api) and click `Create New Token`. Give your token a name (such as "Alfred" or "Search"), and copy it.
Open the Alfred Preferences, go to `Workflows` and find Kanka. In the top-right corner of the window you'll find a button that looks like `[x]`. Click it to show the Workflow Variables window.
On the right half of the window, find the row that says `token` and double click under the `value` column, then paste your token and click `Save` to exit.

## Usage
```
kk [query]
```
Press <kbd>return</kbd> (↵) to open the selected page.

## Configuration (WIP)
By default, the workflow caches all the entities from all your campaigns up to once every 24 hours, when you call the workflow. If you want to increase or decrease this limit, you may change how many hours must pass between updates by changing the `cache_limit` workflow variable.


## TODO
* Allow configuration of what entity types are included (to help with the API call limit)
* Make decent UI for configuration
* Figure out auto-updating
