#!/usr/bin/env python3
from bs4 import BeautifulSoup
from fluent_discourse import Discourse
import json
from docopt import docopt
from hashlib import sha1
import sys


def print_to_stderr(*a, **k):
    print(*a, file=sys.stderr, **k)


debug = False
debug_log = print_to_stderr if debug else lambda *a, **k: None

# DocOpt definition of the command line interface.
help = """
Transform posts from discourse to algolia-style. Input is expected to be json on
stdin and output is json on stdout. Allow multiple tags to be specified.

Usage:
    transform-discourse-to-algolia --discourse-url=<discourse-url> --lvl0=<lvl0>  --tag=<tag>...

Options:
    --discourse-url=<discourse-url>  The base url of the discourse forum.
    --lvl0=<lvl0>                    The top level category name to nest all search results under. [default: Forum]
    --tag=<tag>                      The tags to add to all algolia objects. [default: community]
"""

# Python's version of JSON's null
null = None

# Algolia's Record Size Limits
ALGOLIA_OBJECT_SIZE_LIMIT = 10000

HTML_TYPES_EXCLUDED_FROM_INDEX = [
    "aside",
    "img",
]

ALGOLIA_TYPE_FROM_HTML_TYPE = {
    "details": "content",
    "div": "content",
    "p": "content",
    "ul": "content",
    "ol": "content",
    "li": "content",
    "blockquote": "content",
    "pre": "content",
    "code": "content",
    "h1": "lvl3",  # "Forum" is lvl0, category is lvl1, topic is lvl2.
    "h2": "lvl3",  # H2 and H3 are the same to keep the hierarchy simple.
    "h3": "lvl3",
    "h4": "content",
    "h5": "content",
    "h6": "content",
}

ALGOLIA_WEIGHT_FOR_TYPE = {
    "lvl0": 100,
    "lvl1": 90,
    "lvl2": 80,
    "lvl3": 70,
    "lvl4": 60,
    "lvl5": 50,
    "lvl6": 40,
    "content": 0,
}


class TransformDiscourseToAlgolia:
    # inspired by get_records_from_dom: https://github.com/algolia/docsearch-scraper/blob/70509a564fe76b34ab28a81189ee5abd99b1a440/scraper/src/strategies/default_strategy.py#L63

    def __init__(self, discourse_url, raw_categories, raw_posts, lvl0, tags):
        self.base_url = discourse_url
        self._public_categories = self.transform_categories(raw_categories)
        self.algolia_objects = self._transform_posts(
            self._public_categories, raw_posts, lvl0, tags)

    def _transform_posts(self, categories, discourse_posts, lvl0, tags):
        algolia_objects = []
        # Iterate over all_posts
        for post in discourse_posts:
            if self.should_skip_post(post, categories):
                continue
            objects = self._transform_post(post, lvl0, tags, categories)
            algolia_objects.extend(objects)
        return algolia_objects

    def _transform_post(self, post, lvl0, base_tags, categories):
        algolia_objects = []
        lvl1 = categories[post["category_id"]]
        lvl2 = post["topic_title"]
        tags = base_tags.copy()
        if post["topic_accepted_answer"]:
            tags.append("answered")
        url = self.post_url(post, self.base_url)
        # Break up post into sections
        html_elements = self._simple_html_parse(post["cooked"])
        for index, section in enumerate(html_elements):
            text = section["text"]
            html_type = section["element"]
            if (not text or text == '' or html_type in HTML_TYPES_EXCLUDED_FROM_INDEX):
                continue
            if (html_type not in ALGOLIA_TYPE_FROM_HTML_TYPE):
                print_to_stderr(
                    f"WARN: This is content, right? Unknown html element: {html_type}: {text}")
                html_type = "p"
            objects = self._transform_section(
                lvl0, lvl1, lvl2, tags, url, text, html_type, index)
            algolia_objects.extend(objects)
        return algolia_objects

    def _transform_section(self, lvl0, lvl1, lvl2, tags, url, text, html_type, position):
        algolia_objects = []
        algolia_type = ALGOLIA_TYPE_FROM_HTML_TYPE[html_type]
        lvl3 = text if algolia_type == "lvl3" else null
        content = text if algolia_type == "content" else null
        hierarchy = {
            "lvl0": lvl0,
            "lvl1": lvl1,
            "lvl2": lvl2,
            "lvl3": lvl3,
        }
        objects = self._create_objects(
            content, tags, algolia_type, url, hierarchy, position, 0)
        algolia_objects.extend(objects)
        return algolia_objects

    def _create_objects(self, content_chunk, tags, algolia_type, url, hierarchy, position, chunk_start):
        algolia_object = {
            "content": content_chunk,
            "tags": tags,
            "type": algolia_type,
            "url": url,
            "hierarchy": hierarchy,
            "weight": {
                "level": ALGOLIA_WEIGHT_FOR_TYPE[algolia_type],
                "position": position,
            }
        }
        algolia_object['hierarchy_camel'] = (algolia_object['hierarchy'],)
        algolia_object['content_camel'] = algolia_object['content']
        # objectID should be unique and deterministic
        algolia_object["objectID"] = sha1(json.dumps(
            [url, hierarchy, position, chunk_start]).encode('utf-8')).hexdigest()

        if self._object_length_too_long(algolia_object):
            # Split the content into two chunks and recurse
            chunk_end = int(len(content_chunk) / 2)
            first_chunk = content_chunk[:chunk_end]
            second_chunk = content_chunk[chunk_end:]
            objects = self._create_objects(
                first_chunk, tags, algolia_type, url, hierarchy, position, chunk_start)
            objects.extend(self._create_objects(
                second_chunk, tags, algolia_type, url, hierarchy, position, chunk_end))
            return objects
        return [algolia_object]

    def _object_length_too_long(self, algolia_object):
        return len(json.dumps(algolia_object)) > ALGOLIA_OBJECT_SIZE_LIMIT

    def transform_categories(self, raw_categories):
        # Pretty print
        # debug_log(json.dumps(raw_categories, indent=4, sort_keys=True))
        categories = {}
        if not raw_categories:
            return categories
        for category in raw_categories:
            # Don't export read_restricted categories
            if category["read_restricted"]:
                continue
            categories[category["id"]] = category["name"]
        return categories

    def post_url(self, post, base_url):
        return f"{base_url}/t/{post['topic_slug']}/{post['topic_id']}/{post['post_number']}"

    def should_skip_post(self, post, categories):
        url = self.post_url(post, '')
        if post["hidden"]:
            print_to_stderr(f"Skipping hidden topic {url}")
            return True
        if post["deleted_at"]:
            print_to_stderr(f"Skipping deleted topic {url}")
            return True
        if post["category_id"] not in categories:
            print_to_stderr(f"Skipping post without public category: {url}")
            return True
        return False

    def _simple_html_parse(self, html):
        """ parse html into first layer of elements and their text.
        returns an array of objects with element and text keys."""
        soup = BeautifulSoup(html, 'html.parser')
        sections = []
        # print to stderr
        debug_log(f"soup: {soup}")
        for element in soup.children:
            trimmed_text = element.text.strip()
            if trimmed_text == '':
                continue
            debug_log(f"element: {element}")
            sections.append(
                {"element": element.name, "text": trimmed_text})
        return sections


def main(input_textio, output_textio, discourse_url, lvl0, tags):
    # Read input from stdin
    data = json.loads(input_textio.read())
    raw_posts = data["posts"]
    raw_categories = data["categories"]

    # Transform data
    transformer = TransformDiscourseToAlgolia(
        discourse_url, raw_categories, raw_posts, lvl0, tags)
    algolia_objects = transformer.algolia_objects

    # Pretty print to output
    output_textio.write(json.dumps(algolia_objects, indent=4, sort_keys=True))
    print_to_stderr(
        f"Transformed {len(raw_posts)} discourse posts into {len(algolia_objects)} algolia objects.")


# Main function
if __name__ == "__main__":
    # Parse command line arguments
    arguments = docopt(help)
    # Run main function with stdin and stdout
    discourse_url = arguments['--discourse-url']
    lvl0 = arguments['--lvl0']
    tags = arguments['--tag']  # list
    main(sys.stdin, sys.stdout, discourse_url, lvl0, tags)
