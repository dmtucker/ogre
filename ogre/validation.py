"""
OGRe Parameter Validator

:func:`validate` -- check OGRe parameters for errors

:func:`sanitize` -- validate and cleanse OGRe parameters
"""


import collections


Interval = collections.namedtuple('Interval', ('earliest', 'latest'))


def validate_interval(interval):
    """Ensure Interval invariants."""

    float(interval.earliest)
    assert interval.earliest >= 0

    float(interval.latest)
    assert interval.latest >= 0


Location = collections.namedtuple('Location', ('latitude', 'longitude', 'radius', 'unit'))


def validate_location(location):
    """Ensure Location invariants."""

    float(location.latitude)
    assert -90 <= location.latitude <= 90

    float(location.longitude)
    assert -180 <= location.latitude <= 180

    float(location.radius)
    assert location.radius > 0

    str(location.unit)
    assert location.unit in ('km', 'mi')


Query = collections.namedtuple('Query', ('media', 'keyword', 'quantity', 'location', 'interval'))


def validate_query(query):
    """Ensure Query invariants."""

    assert all([True for medium in query.media if medium in ('image', 'sound', 'text', 'video')])

    str(query.keyword)

    int(query.quantity)
    assert query.quantity >= 0

    if query.location is not None:
        validate_location(query.location)

    if query.interval is not None:
        validate_interval(query.interval)


def validate(
        media=("image", "sound", "text", "video"),
        keyword="",
        quantity=15,
        location=None,
        interval=None,
):  # pylint: disable=too-many-branches

    """
    Check common interface parameters for errors and validity.

    :type media: tuple
    :param media: "image", "sound", "text", and "video" are valid mediums.

    :type keyword: str
    :param keyword: Valid criteria varies by source.

    :type quantity: int
    :param quantity: Specify a positive quota of desired results.

    :type location: tuple
    :param location: Specify a location (latitude, longitude, radius, unit)
                     composed of 3 numbers and a string, respectively.
                     "km" and "mi" are supported units.

    :type interval: tuple
    :param interval: Specify a period of time (earliest, latest)
                     composed of 2 POSIX timestamps (positive numbers).
                     The order of earliest/latest moments does not matter as
                     the lower number will be considered earliest.

    :raises: ValueError
    """

    if media is not None:
        for medium in media:
            medium = medium.lower()
            if medium not in (
                    "image",
                    "sound",
                    "text",
                    "video"
            ):
                raise ValueError(
                    'Medium may be "image", "sound", "text", or "video".'
                )

    try:
        str(keyword)
    except:
        raise ValueError("Keyword must be a string.")

    if int(quantity) < 0:
        raise ValueError("Quantity must be positive.")

    if location is not None:
        if len(location) != 4:
            raise ValueError(
                "usage: where=(latitude, longitude, radius, unit)"
            )
        latitude = float(location[0])
        if latitude < -90 or latitude > 90:
            raise ValueError("Latitude must be -90 to 90.")
        longitude = float(location[1])
        if longitude < -180 or longitude > 180:
            raise ValueError("Longitude must be -180 to 180.")
        radius = float(location[2])
        if radius < 0:
            raise ValueError("Radius must be positive.")
        unit = location[3].lower()
        if unit not in ("km", "mi"):
            raise ValueError('Unit must be "km" or "mi".')

    if interval is not None:
        if len(interval) != 2:
            raise ValueError("usage: when=(earliest, latest)")
        since = float(interval[0])
        if since < 0:
            raise ValueError("Earliest moment must be POSIX timestamps.")
        until = float(interval[1])
        if until < 0:
            raise ValueError("Latest moment must be POSIX timestamps.")


def sanitize(
        media=("image", "sound", "text", "video"),
        keyword="",
        quantity=15,
        location=None,
        interval=None,
):  # pylint: disable=too-many-locals

    """Validate and transform input to expected types.

    .. seealso:: :meth:`validate` describes the format each
                 parameter must have.

    :type media: tuple
    :param media: Specify content mediums to make lowercase and deduplicate.

    :type keyword: str
    :param keyword: Specify search criteria.

    :type quantity: int
    :param quantity: Specify a quota of results.

    :type location: tuple
    :param location: Specify a location to make numeric
                     (latitude, longitude, radius) and lowercase (unit).

    :type interval: tuple
    :param interval: Specify earliest and latest moments to make numeric and
                     sort in ascending order.

    :rtype: tuple
    :returns: sanitized parameters
              (media, keyword, quantity, location, interval)

    """

    validate(
        media=media,
        keyword=keyword,
        quantity=quantity,
        location=location,
        interval=interval
    )

    clean_media = []
    if media is not None:
        for medium in media:
            medium = medium.lower()
            if medium not in clean_media:
                clean_media.append(medium)

    clean_media = tuple(clean_media)  # pylint: disable=redefined-variable-type
    clean_keyword = str(keyword)
    clean_quantity = int(quantity)

    clean_location = None
    if location is not None:
        latitude = float(location[0])
        longitude = float(location[1])
        radius = float(location[2])
        unit = location[3].lower()
        clean_location = (latitude, longitude, radius, unit)

    clean_interval = None
    if interval is not None:
        since = float(interval[0])
        until = float(interval[1])
        if since > until:
            since, until = until, since
        clean_interval = (since, until)

    return (
        clean_media,
        clean_keyword,
        clean_quantity,
        clean_location,
        clean_interval
    )
