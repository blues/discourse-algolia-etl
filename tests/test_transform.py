import unittest
import json
from unittest.mock import patch
from hashlib import sha1

from src.transform_discourse_to_algolia import TransformDiscourseToAlgolia
from .data import LONG_POST, RAW_CATEGORIES, RAW_POSTS


class TestDiscourseAlgolia(unittest.TestCase):
    maxDiff = None

    # to declare a variable readonly in python use all caps it's not enforced
    # but it's a convention. to enforce it you can use the mypy linter.
    LVL0 = "Forum"

    TAGS = ["tag1", "tag2"]

    # Set up a transformer for each test
    def setUp(self):
        self.transformer = TransformDiscourseToAlgolia(
            "http://example.com", RAW_CATEGORIES, RAW_POSTS, self.LVL0, self.TAGS)

    def test_post_url(self):
        base_url = 'http://test.com'
        post = RAW_POSTS[0].copy()
        result = self.transformer.post_url(post, base_url)

        self.assertEqual(
            result, 'http://test.com/t/ftdi-debugging-with-notecarrier-b-v2/1436/4')

    def test_should_skip_post_should_not_for_good_post(self):
        post = RAW_POSTS[0].copy()
        result = self.transformer.should_skip_post(
            post, {1: "test category"})
        self.assertFalse(result)

    def test_should_skip_post_if_hidden(self):
        post = RAW_POSTS[0].copy()
        post['hidden'] = True
        result = self.transformer.should_skip_post(
            post, {1: "test category"})
        self.assertTrue(result)

    def test_should_skip_post_if_deleted(self):
        post = RAW_POSTS[0].copy()
        post['deleted_at'] = '2023-03-23T02:19:58.928Z'
        result = self.transformer.should_skip_post(
            post, {1: "test category"})
        self.assertTrue(result)

    def test_should_skip_post_if_category_not_in_categories(self):
        post = RAW_POSTS[0].copy()
        post['category_id'] = 2
        result = self.transformer.should_skip_post(
            post, {1: "test category"})
        self.assertTrue(result)

    def test_simple_html_parse(self):
        html = "<h1>header</h1><p><em>cool</em> test</p>"
        result = self.transformer._simple_html_parse(html)
        expected_result = [
            {'element': 'h1', 'text': 'header'},
            {'element': 'p', 'text': 'cool test'},
        ]
        self.assertEqual(result, expected_result)

    def test_simple_html_parse_with_empty_string(self):
        html = ""
        result = self.transformer._simple_html_parse(html)
        expected_result = []
        self.assertEqual(result, expected_result)

    def test_simple_html_parse_trims_whitespace(self):
        html = "<h1>header</h1><p> <em>cool</em> test</p>"
        result = self.transformer._simple_html_parse(html)
        expected_result = [
            {'element': 'h1', 'text': 'header'},
            {'element': 'p', 'text': 'cool test'},
        ]
        self.assertEqual(result, expected_result)

    def test_transform_categories(self):
        raw_categories = RAW_CATEGORIES.copy()
        result = self.transformer.transform_categories(raw_categories)
        expected_result = {1: 'Uncategorized', 2: 'Feedback'}
        self.assertEqual(result, expected_result)

    def test_transform_categories_with_read_restricted(self):
        raw_categories = RAW_CATEGORIES.copy()
        raw_categories[0]['read_restricted'] = True
        result = self.transformer.transform_categories(raw_categories)
        expected_result = {2: 'Feedback'}
        self.assertEqual(result, expected_result)

    def test_transform_categories_with_empty_categories(self):
        raw_categories = []
        result = self.transformer.transform_categories(raw_categories)
        expected_result = {}
        self.assertEqual(result, expected_result)

    def test_transform_categories_with_no_categories(self):
        result = self.transformer.transform_categories(None)
        expected_result = {}
        self.assertEqual(result, expected_result)

    def test_create_object_for_content(self):
        content = "test content"
        tags = ["tag1", "tag2"]
        type = "content"
        url = "http://example.com"
        hierarchy = {"lvl0": "Forum", "lvl1": "Uncategorized",
                     "lvl2": "test title", "lvl3": None}
        position = 2
        chunk_start = 0
        result = self.transformer._create_objects(
            content, tags, type, url, hierarchy, position, chunk_start)
        expected_result = [{
            "content": "test content",
            "content_camel": "test content",
            "tags": ["tag1", "tag2"],
            "type": "content",
            "url": "http://example.com",
            "hierarchy": {"lvl0": "Forum", "lvl1": "Uncategorized",
                          "lvl2": "test title", "lvl3": None},
            "weight": {
                "level": 0,
                "position": 2,
            },
            "hierarchy_camel": ({"lvl0": "Forum", "lvl1": "Uncategorized",
                                "lvl2": "test title", "lvl3": None},),
            "objectID": "625eb2ac0071d8dba4dad442e45402790ce6b20b"
        }]
        self.assertEqual(result, expected_result)

    def test_transform_section_with_short_content(self):
        lvl0 = "Forum"
        lvl1 = "Uncategorized"
        lvl2 = "test title"
        tags = ["tag1", "tag2"]
        url = "http://example.com"
        text = "test content"
        html_type = "p"
        position = 2
        result = self.transformer._transform_section(
            lvl0, lvl1, lvl2, tags, url, text, html_type, position)
        expected_result = [{
            "content": "test content",
            "content_camel": "test content",
            "tags": ["tag1", "tag2"],
            "type": "content",
            "url": "http://example.com",
            "hierarchy": {"lvl0": "Forum", "lvl1": "Uncategorized",
                          "lvl2": "test title", "lvl3": None},
            "weight": {
                "level": 0,
                "position": 2,
            },
            "hierarchy_camel": ({"lvl0": "Forum", "lvl1": "Uncategorized",
                                "lvl2": "test title", "lvl3": None},),
            "objectID": "625eb2ac0071d8dba4dad442e45402790ce6b20b"
        }]
        self.assertEqual(result, expected_result)

    def test_transform_section_with_long_content(self):
        lvl0 = "Forum"
        lvl1 = "Troubleshooting"
        lvl2 = "Web requests: sending images mostly fails"
        tags = ["community"]
        url = "https://discuss.blues.io/t/web-requests-sending-images-mostly-fails/1437/3"
        text = self.transformer._simple_html_parse(
            LONG_POST['cooked'])[8]['text']
        html_type = "p"
        position = 16

        result = self.transformer._transform_section(
            lvl0, lvl1, lvl2, tags, url, text, html_type, position)
        # no items should be more than 10k when converted to json with no whitespace.
        self.assertGreater(len(result), 1)
        for item in result:
            json_item = json.dumps(item, separators=(',', ':'))
            self.assertLessEqual(len(json_item), 10000, json_item)
        # All items put together should be more than 10k
        json_result = json.dumps(result, separators=(',', ':'))
        self.assertGreater(len(json_result), 10000, json_result)

    def test_transform_section_header(self):
        lvl0 = "Forum"
        lvl1 = "Uncategorized"
        lvl2 = "Thread Title"
        tags = ["tag1", "tag2"]
        url = "http://example.com"
        text = "Header within the Post"
        html_type = "h1"
        position = 8
        result = self.transformer._transform_section(
            lvl0, lvl1, lvl2, tags, url, text, html_type, position)
        expected_result = [{
            "content": None,
            "content_camel": None,
            "tags": ["tag1", "tag2"],
            "type": "lvl3",
            "url": "http://example.com",
            "hierarchy": {"lvl0": "Forum", "lvl1": "Uncategorized",
                          "lvl2": "Thread Title", "lvl3": "Header within the Post"},
            "weight": {
                "level": 70,
                "position": 8,
            },
            "hierarchy_camel": ({"lvl0": "Forum", "lvl1": "Uncategorized",
                                "lvl2": "Thread Title", "lvl3": "Header within the Post"},),
            "objectID": "016b8eedc3e5c2dcab5389e22b97caf11c6da24c"
        }]
        self.assertEqual(result, expected_result)

    def test_transform_post(self):
        lvl0 = "Forum"
        tags = ["tag1", "tag2"]
        post = LONG_POST.copy()
        post['category_id'] = 13
        post['topic_accepted_answer'] = True
        post['cooked'] = "<h1>Header within the Post</h1><p>Content within the Post</p>"
        categories = {13: "Troubleshooting"}
        result = self.transformer._transform_post(post, lvl0, tags, categories)
        expected_result = [{
            "content": None,
            "content_camel": None,
            "tags": ["tag1", "tag2", "answered"],
            "type": "lvl3",
            "url": "http://example.com/t/web-requests-sending-images-mostly-fails/1437/3",
            "hierarchy": {"lvl0": "Forum", "lvl1": "Troubleshooting",
                          "lvl2": "Web requests: sending images mostly fails", "lvl3": "Header within the Post"},
            "weight": {
                "level": 70,
                "position": 0,
            },
            "hierarchy_camel": ({"lvl0": "Forum", "lvl1": "Troubleshooting",
                                "lvl2": "Web requests: sending images mostly fails", "lvl3": "Header within the Post"},),
            "objectID": "286b8ec2defa142702129411e8fd3197d17d2c5b"
        }, {
            "content": "Content within the Post",
            "content_camel": "Content within the Post",
            "tags": ["tag1", "tag2", "answered"],
            "type": "content",
            "url": "http://example.com/t/web-requests-sending-images-mostly-fails/1437/3",
            "hierarchy": {"lvl0": "Forum", "lvl1": "Troubleshooting",
                          "lvl2": "Web requests: sending images mostly fails", "lvl3": None},
            "weight": {
                "level": 0,
                "position": 1,
            },
            "hierarchy_camel": ({"lvl0": "Forum", "lvl1": "Troubleshooting",
                                "lvl2": "Web requests: sending images mostly fails", "lvl3": None},),
            "objectID": "edcb49e8f90a14485eadc3d8806b74492737bbc3"
        }]
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
