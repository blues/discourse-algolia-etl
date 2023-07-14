#!/usr/bin/env python3

from docopt import docopt
from fluent_discourse import Discourse
import json
import sys

# DocOpt definition of the command line interface.
help = """ Extract posts and categories from Discourse to stdout.

Usage:
    discourse-extract

Environment Variables:
    DISCOURSE_URL       The URL of the Discourse instance.
    DISCOURSE_USERNAME  The username to use for the Discourse API.
    DISCOURSE_API_KEY   The API key to use for the Discourse API.
"""


def print_to_stderr(*a, **k):
    print(*a, file=sys.stderr, **k)


def extract_posts():
    # Make sure to set DISCOURSE_URL, DISCOURSE_USERNAME, and DISCOURSE_API_KEY
    client = Discourse.from_env(raise_for_rate_limit=False)

    all_posts = []
    none_yet = 0
    earliest_extracted_post_id = none_yet
    while earliest_extracted_post_id != 1:
        print_to_stderr(f"Fetching posts before {earliest_extracted_post_id}")
        posts = client.posts.json.get({"before": earliest_extracted_post_id})
        all_posts.extend(posts["latest_posts"])
        last_post = posts["latest_posts"][-1]
        earliest_extracted_post_id = last_post["id"]
    return all_posts


def extract_categories():
    # Make sure to set DISCOURSE_URL, DISCOURSE_USERNAME, and DISCOURSE_API_KEY
    client = Discourse.from_env(raise_for_rate_limit=False)
    site = client.site.json.get()
    raw_categories = site["categories"]
    return raw_categories


# Main function
if __name__ == "__main__":
    # Parse arguments
    arguments = docopt(help)
    # Extract posts
    data = {
        "posts": extract_posts(),
        "categories": extract_categories()
    }
    # pretty print data
    print(json.dumps(data, indent=2))
