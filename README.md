# Discourse => Algolia ETL (Extract Transform Load)

This repo contains tools to extract content from a Discourse forum and load
it into Algolia in a shape that is compatible with Algolia DocSearch.

To satisfy DocSearch, the objects created in Algolia are of two types:

1. `content` - Text from a paragraph in a post. Hierarchical information is
   included in the object lvl0, lvl1, lvl2, lvl3. (see below)
2. `lvl3` - Contextual objects for headers (h2, h3, etc) within the content.

These types are based on the types created by the open source
[docsearch-scraper](https://github.com/algolia/docsearch-scraper) which is a
very useful tool for scraping static sites.

## Usage

```bash
./setup # install dependencies
./main-etl all
```

## Runtime Environment

### Python

This tool was developed with python 3.9.

## Configuration

The configuration is done via environment variables. The following variables
must be set:

### Required Config

```bash
# The Discourse API needs read access to the forum you're trying to index.
export DISCOURSE_API_KEY=...
export DISCOURSE_URL=...
export DISCOURSE_USERNAME=...
# The Algolia API needs write access to the index you're trying to update.
export ALGOLIA_API_KEY=...
export ALGOLIA_APP_ID=...
export ALGOLIA_INDEX_NAME=...
```

### Optional Config

#### Hierarchy Levels

```bash
export ALGOLIA_LVL0=... # (default: Forum)
```

The ALGOLIA_LVL0 is the top level name for when results show up in DocSearch.
For example, if you set ALGOLIA_LVL0 to "Forum", then all results will show up
under the "Forum" category.

    ```text
    Forum > {Category Name} > {Topic Name} > {Section Name, h1, h2, etc.}
    e.g.
    Forum > Hardware > What antenna should I use? > Cellular
    ```

#### Algolia Tags

```bash
export ALGOLIA_TAG=...  # (default: community)
```

The ALGOLIA_TAG is a tag that will be added to all objects in Algolia. This is
useful in the DocSearch UI for filtering or tagging results as being from a
certain source.

#### Not Configurable

```
answered
```

All posts in a Discourse marked 'Answered' will _also_ be tagged "answered", in
addition to the ALGOLIA_TAG. Posts in unanswered topics will not get an extra
tag. This is not yet configurable but a developer could follow the lead of the
ALGOILA_TAG and add a new environment variable to control this.

## Esoteric details

Algolia limits objects to 10kb, so if we find a large paragraph, we split it
in half repeatedly until it is small enough to fit. This is done in the
transform step.

## Advanced Usage

To do a subset of the steps, use one of:

```bash
./main-etl extract
./main-etl transform
./main-etl load
./main-etl extract transform
./main-etl transform load
```

## Debugging

### Extract

The Extract step creates a file called [`discourse.json`](discourse.json) This
file contains the raw json from the Discourse API.

### Transform

The Transform step creates a file called [`algolia.json`](algolia.json) This
file contains the json that will be sent to Algolia.

## Development

### Python

If you use the vscode devcontainer, you'll get a python environment with the
correct version of python. Otherwise, you'll want to install python 3.9.\*.

### Setup

```bash
./setup # install dependencies
```

### Testing

The tests were written with the python unittest framework. There are two ways to
run the tests.

The easiest is to install the vscode extension `Python Test Explorer UI` and run
the tests from there.

The other way is to run the tests from the command line:

```bash
./setup # install dependencies
python3 -m unittest discover
```

#### Tip

Debug the tests from top to bottom in the
[`tests/test_transform.py`](tests/test_transform.py)

## Submodules

### Extract

The [src/extract_discourse.py](src/extract_discourse.py) file contains the
extraction logic.

```plaintext
$ src/extract_discourse.py --help
 Extract posts and categories from Discourse to stdout.

Usage:
    discourse-extract

Environment Variables:
    DISCOURSE_API_KEY   The API key to use for the Discourse API.
    DISCOURSE_URL       The URL of the Discourse instance.
    DISCOURSE_USERNAME  The username to use for the Discourse API.
```

### Transform

The
[src/transform_discourse_to_algolia.py](src/transform_discourse_to_algolia.py)
file contains the transformation logic.

```plaintext
$ src/transform_discourse_to_algolia.py --help
 Transform posts from discourse to algolia-style. Input is expected to be json on
stdin and output is json on stdout. Allow multiple tags to be specified.

Usage:
    transform-discourse-to-algolia --discourse-url=<discourse-url> --lvl0=<lvl0>  --tag=<tag>...

Options:
    --discourse-url=<discourse-url>  The base url of the discourse forum.
    --lvl0=<lvl0>                    The top level category name to nest all search results under. [default: Forum]
    --tag=<tag>                      The tags to add to all algolia objects. [default: community]
```

### Load

The [src/load_algolia.py](src/load_algolia.py) file contains the loading logic.

```plaintext
$ src/load_algolia.py --help
Load objects into Algolia from a file via the Algolia API.

Usage:
    load-algolia <algolia-json-file> <algolia-index-name>

Environment Variables:
    ALGOLIA_APP_ID
    ALGOLIA_API_KEY
```

> Credits
>
> Hats off to github copilot for translating my thoughts into python.
