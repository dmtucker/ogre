"""
Make queries using OGRe directly.

See https://ogre.readthedocs.org/en/latest/ for more information.
"""

from __future__ import absolute_import

import argparse
import json
import logging
import os
import sys

import ogre.api


def cli(parser=None):
    """Define a CLI."""
    if parser is None:
        parser = argparse.ArgumentParser(description="OpenFusion GeoJSON Retriever")
    parser.add_argument(
        "--keys",
        help="Specify API keys.",
        default=None,
    )
    parser.add_argument(
        "-s", "--sources",
        help="Specify public APIs to get content from (required)." +
        " 'Twitter' is currently the only supported source.",
        action="append",
        required=True,
    )
    parser.add_argument(
        "-m", "--media",
        help="Specify content mediums to fetch." +
        " 'image', 'sound', 'text', and 'video' are supported.",
        default=None,
        action="append",
    )
    parser.add_argument(
        "-k", "--keyword",
        help="Specify search criteria.",
        default="",
    )
    parser.add_argument(
        "-q", "--quantity",
        help="Specify a quota of results to fetch.",
        type=int,
        default=15,
    )
    parser.add_argument(
        "-l", "--location",
        help="Specify a place (latitude, longitude, radius, unit) to search." +
        " 'km' and 'mi' are supported units.",
        default=None,
        nargs=4,
    )
    parser.add_argument(
        "-i", "--interval",
        help="Specify a period of time (earliest, latest) to search." +
        " Each moment should be a POSIX timestamp.",
        default=None,
        nargs=2,
    )
    parser.add_argument(
        "--hard",
        help="Fail hard (Raise exceptions instead of returning empty).",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--insecure",
        help="Prefer HTTP.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--limit",
        help="Specify a query limit.",
        default=None,
    )
    parser.add_argument(
        "--log",
        help="Specify a log level.",
        default=None,
    )
    parser.add_argument(
        "--strict",
        help="Ensure resulting media is specifically requested.",
        action="store_true",
        default=False,
    )
    return parser


def main(argv=None):
    """Process arguments and invoke OGRe to fetch some data."""

    if argv is None:
        argv = sys.argv[1:]
    args = cli().parse_args(argv)

    if args.keys is not None:
        args.keys = json.loads(args.keys)
    else:
        args.keys = {
            "Twitter": {
                "consumer_key": os.environ.get("TWITTER_CONSUMER_KEY"),
                "access_token": os.environ.get("TWITTER_ACCESS_TOKEN"),
            },
        }
    if args.media is None:
        args.media = ("image", "sound", "text", "video")
    if args.location is not None:
        args.location[0] = float(args.location[0])
        args.location[1] = float(args.location[1])
        args.location[2] = float(args.location[2])
    if args.interval is not None:
        args.interval[0] = float(args.interval[0])
        args.interval[1] = float(args.interval[1])
    if args.limit is not None:
        args.limit = int(args.limit)
    if args.log is not None:
        args.log = getattr(logging, args.log.upper())
    else:
        args.log = logging.WARN

    logging.basicConfig(
        level=args.log,
        format="%(asctime)s.%(msecs)03d %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print(
        json.dumps(
            ogre.api.OGRe(args.keys).fetch(
                sources=args.sources,
                media=args.media,
                keyword=args.keyword,
                quantity=args.quantity,
                location=args.location,
                interval=args.interval,
                fail_hard=args.hard,
                query_limit=args.limit,
                secure=args.insecure,
                strict_media=args.strict,
            ),
            indent=4,
            separators=(",", ": "),
        ),
    )
