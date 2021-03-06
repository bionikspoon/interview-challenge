# coding=utf-8
"""
Example: python2 solution.py --verbose -u http://interview-challenge.manuphatak.com
"""

import logging
import sys
from argparse import ArgumentParser
from functools import partial
from textwrap import dedent
from urllib.parse import urljoin

import requests


#
# ARGPARSE
# ============================================================================


parser = ArgumentParser(
    description="Solution to scavenger hunt.",
    epilog="Example: python solution.py --verbose -u http://localhost:5000",
)
parser.add_argument(
    "-b",
    "--base",
    default="http://localhost:5000",
    help="Base URL of the scavenger hunt. Default: http://localhost:5000",
)

parser.add_argument(
    "--verbose",
    "-v",
    help="Show detailed output",
    action="store_const",
    const=logging.DEBUG,
    default=logging.INFO,
    dest="log_level",
)
args = parser.parse_args()

#
# GLOBALS
# ============================================================================
log = logging.getLogger(__name__)
create_url = partial(urljoin, args.base)

headers = {}


#
# CORE
# ============================================================================


def get_next_secret(path):
    """Recursively follow a path to yield secrets."""

    # Setup, get next resource
    response = request_next(create_url(path))
    # clean response data
    response_data = normalize_keys(response.json())

    # Guard, response is a leaf
    if "secret" in response_data:
        secret = response_data["secret"]
        log_secret_found(secret, create_url(path))
        yield secret

    # Guard, missing next node.
    elif not response_data.get("next"):
        traceback = sys.exc_info()[2]
        message = 'Missing "next" key in response'
        log_response_error(
            message, headers.get("Session"), create_url(path), response_data
        )
        raise (KeyError, message, traceback)

    else:
        next_list = response_data["next"]
        log_next_list(next_list)

        # traverse each child branch
        for next_path in next_list:
            # yield from results
            for next_secret in get_next_secret(next_path):
                yield next_secret


def request_next(path, is_retry=False):
    """Handle requests with custom headers."""

    # Setup, get resource
    response = requests.get(create_url(path), headers=headers)
    response_json = response.json()

    # handle 404 response
    try:
        response.raise_for_status()
    except requests.HTTPError as e:

        # Guard, infinite loop
        if is_retry:
            traceback = sys.exc_info()[2]
            message = 'Unable to refresh "Session" token.'
            log_response_error(
                message, headers["Session"], create_url(path), response_json
            )
            raise (type(e), message, traceback)

        # Guard, unexpected error
        if not response_json.get("error"):
            traceback = sys.exc_info()[2]
            message = '"error" key missing from response.'
            log_response_error(
                message, headers["Session"], create_url(path), response_json
            )
            raise (type(e), message, traceback)

        # request new Session header
        headers["Session"] = requests.get(create_url("get-session")).text
        log.info('NEW "Session" token: %s', headers["Session"])

        # retry request with updated headers
        return request_next(path, is_retry=True)

    log.info("GET %s %s", create_url(path), response_json.get("secret") or "")
    log.debug("Response: %s", response.text)
    return response


#
# UTILS
# ============================================================================


def normalize_keys(data):
    """Convert keys to lowercase"""
    return {k.lower(): v for k, v in data.items()}


#
# LOG UTILS
# ============================================================================


def log_next_list(next_list):
    template = dedent(
        """

        {log_header_1}
        Next list
        {log_header_2}
        {next_list}
        {log_header_1}
    """[
            1:
        ]
    )
    template_vars = {
        "log_header_1": "=" * 70,
        "log_header_2": "-" * 70,
        "next_list": "\n".join(next_list),
    }

    log.debug(template.format(**template_vars))


def log_secret_found(secret, full_url):
    template = dedent(
        """

        {log_header_1}
        Secret Found
        {log_header_2}
        Url: {url}
        Secret: {secret}
        {log_header_1}
    """[
            1:
        ]
    )
    template_vars = {
        "log_header_1": "-" * 70,
        "log_header_2": "~" * 70,
        "url": full_url,
        "secret": secret,
    }

    log.debug(template.format(**template_vars))


def log_response_error(message, session, full_url, response):
    log.error(message)
    log.error("  - SESSION: %s", session)
    log.error("  - URL: %s", full_url)
    log.error("  - RESPONSE: %s", response)


#
# MAIN
# ============================================================================
def run():
    logging.basicConfig(level=args.log_level)
    logging.getLogger("requests").setLevel(logging.WARNING)

    try:
        parser.exit(0, "".join(get_next_secret("start")))
    except Exception as error:
        parser.error(error)


if __name__ == "__main__":
    run()
