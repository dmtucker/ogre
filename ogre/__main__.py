#!/usr/bin/env python

"""Make queries using OGRe directly.

usage: ogre [(-s|--sources) Twitter]
    [--keys "<dict>"]
    [(-m|--media) (image|sound|text|video)]
    [(-k|--keyword) <str>]
    [(-q|--quantity) <int>]
    [(-l|--location) <longitude> <latitude> <radius> (km|mi)]
    [(-i|--interval) <since> <until>]
    [(-h|--help)]
    [--insecure]
    [--strict]

See https://ogre.readthedocs.org/en/latest/ for more information.

"""

import argparse
import json
import os
from ogre import OGRe


def main():

    """Process arguments and invoke OGRe to fetch some data."""

    parser = argparse.ArgumentParser(description="OpenFusion GIS Retriever")
    parser.add_argument(
        "--keys",
        help="Specify API keys.",
        default=None
    )
    parser.add_argument(
        "-s", "--sources",
        help="Specify public APIs to get content from (required)." +
             " 'Twitter' is currently the only supported source.",
        action="append",
        required=True
    )
    parser.add_argument(
        "-m", "--media",
        help="Specify content mediums to fetch." +
             " 'image', 'sound', 'text', and 'video' are supported.",
        default=None,
        action="append"
    )
    parser.add_argument(
        "-k", "--keyword",
        help="Specify search criteria.",
        default=""
    )
    parser.add_argument(
        "-q", "--quantity",
        help="Specify a quota of results to fetch.",
        type=int,
        default=15
    )
    parser.add_argument(
        "-l", "--location",
        help="Specify a place (latitude, longitude, radius, unit) to search." +
             " 'km' and 'mi' are supported units.",
        default=None,
        nargs=4
    )
    parser.add_argument(
        "-i", "--interval",
        help="Specify a period of time (earliest, latest) to search." +
             " Each moment should be a POSIX timestamp.",
        default=None,
        nargs=2
    )
    parser.add_argument(
        "--insecure",
        help="Prefer HTTP.",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "--strict",
        help="Ensure resulting media is specifically requested.",
        action="store_true",
        default=False
    )
    args = parser.parse_args()

    if args.keys is not None:
        args.keys = json.loads(args.keys)
    else:
        args.keys = {
            "Twitter": {
                "consumer_key": os.environ.get("TWITTER_CONSUMER_KEY"),
                "access_token": os.environ.get("TWITTER_ACCESS_TOKEN")
            }
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

    print json.dumps(
        OGRe(args.keys).fetch(
            sources=args.sources,
            media=args.media,
            keyword=args.keyword,
            quantity=args.quantity,
            location=args.location,
            interval=args.interval,
            secure=args.insecure,
            strict_media=args.strict
        ),
        indent=4,
        separators=(",", ": ")
    )


if __name__ == "__main__":
    main()
