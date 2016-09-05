"""
OGRe Query Handler

:class:`OGRe` -- retriever object template

:meth:`OGRe.fetch` -- method for making a retriever fetch data
"""


from __future__ import absolute_import

import ogre.twitter


class OGRe(object):  # pylint: disable=too-few-public-methods

    """
    Create objects that contain API keys and API access points.

    OGRe was made a class to avoid requiring API keys with every API call.
    Since this is a library meant for developers,
    it didn't seem appropriate to use a configuration file.
    Also, importing the keys from the OS environment subjects them to data leak.
    This way developers are responsible for keeping their keys safe,
    and they can use the environment if they choose.
    Twython, the Twitter API wrapper, also uses this scheme.

    :meth:`fetch` -- method for retrieving data from a public source
    """

    def __init__(self, keys):
        """
        Instantiate an OGRe.

        :type keys: dict
        :param keys: Specify dictionaries containing API keys for sources.
        """
        self.keys = {source.lower(): key for source, key in keys.items()}

    def fetch(
            self,
            sources,
            media=('image', 'sound', 'text', 'video'),
            keyword='',
            quantity=15,
            location=None,
            interval=None,
            **kwargs
    ):  # pylint: disable=too-many-arguments

        """
        Get geotagged data from public APIs.

        .. seealso:: :meth:`ogre.validation.validate` describes the format each
                     parameter must have.
                     It is also a good idea to check the module of any sources
                     that will be searched
                     (e.g. :meth:`ogre.Twitter.twitter`)
                     for extra constraints on parameters.

        :type sources: tuple
        :param sources: Specify public APIs to get content from (required).
                        "Twitter" is currently the only supported source.

        :type media: tuple
        :param media: Specify content mediums to fetch.
                      "image", "sound", "text", and "video" are supported.

        :type keyword: str
        :param keyword: Specify search criteria.

        :type quantity: int
        :param quantity: Specify a quota of results to fetch.

        :type location: tuple
        :param location: Specify a place (latitude, longitude, radius, unit)
                         to search.

        :type interval: tuple
        :param interval: Specify a period of time (earliest, latest) to search.

        :raises: ValueError

        :rtype: dict
        :returns: GeoJSON FeatureCollection

        .. note:: Additional runtime modifiers may be specified to change
                  the way results are retrieved.
                  Runtime modifiers are relayed to each source module,
                  and that is where they are documented.
        """

        supported_sources = {'twitter': ogre.twitter.fetch}

        feature_collection = {
            'type': 'FeatureCollection',
            'features': [],
        }
        if media and quantity > 0:
            for source in [source.lower() for source in sources]:
                if source not in supported_sources:
                    raise ValueError(
                        '"{0}" is an unrecognized source.'
                        ' Valid sources are {1}.'.format(source, supported_sources.keys()),
                    )
                feature_collection['features'].extend(
                    supported_sources[source](
                        ogre.objects.Query(*(media, keyword, quantity, location, interval)),
                        self.keys[source],
                        **kwargs
                    )['features'],
                )
        return feature_collection
