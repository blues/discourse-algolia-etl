#!/usr/bin/env python3
from algoliasearch.search_client import SearchClient
from docopt import docopt
import json
import os
import sys


def print_to_stderr(*a, **k):
    print(*a, file=sys.stderr, **k)


debug = False
debug_log = print_to_stderr if debug else lambda *a, **k: None

# DocOpt definition of the command line interface.
help = """
Load objects into Algolia from a file via the Algolia API.

Usage:
    load-algolia <algolia-json-file> <algolia-index-name>

Environment Variables:
    ALGOLIA_APP_ID
    ALGOLIA_API_KEY
"""


def load(algolia_index_name, algolia_app_id, algolia_api_key, json_file):
    # Load the Algolia API client
    client = SearchClient.create(algolia_app_id, algolia_api_key)
    index = client.init_index(algolia_index_name)

    # Load the JSON file
    with open(json_file) as f:
        objects = json.load(f)

    # Push the objects to Algolia
    print_to_stderr(f"Loading {len(objects)} objects...")
    # first just send 10 objects
    index.save_objects(objects).wait()

    return len(objects)


# Main function
if __name__ == "__main__":
    # Parse arguments
    arguments = docopt(help)
    debug_log(arguments)
    algolia_index_name = arguments['<algolia-index-name>']
    json_file = arguments['<algolia-json-file>']

    # Get environment variables
    algolia_app_id = os.environ.get('ALGOLIA_APP_ID')
    algolia_api_key = os.environ.get('ALGOLIA_API_KEY')

    # Load the objects into Algolia
    count = load(algolia_index_name, algolia_app_id,
                 algolia_api_key, json_file)

    # Print summary
    print(f"Loaded {count} objects into index '{algolia_index_name}'")
