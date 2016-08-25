"""
OGRe Query Handler

:class:`OGRe` -- retriever object template

:meth:`OGRe.fetch` -- method for making a retriever fetch data
"""

from ogre.Twitter import twitter


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

        Keys that a retriever object is instantiated with may be accessed later
        through the :attr:`keychain` attribute.

        :raises: ValueError

        .. note:: A :attr:`keyring` attribute maintains a mapping of the
                  lowercase version of each key to the casing of the passed key.
                  This enables you to pass a key with a name stylized in the
                  manner of your choosing
                  (e.g. twitter, Twitter, tWiTtEr, etc.).
        """
        self.keyring = {}
        for key in keys:
            if key.lower() not in ["twitter"]:
                raise ValueError('Keys may include "Twitter" only.')
            self.keyring[key.lower()] = key
        self.keychain = keys

    def fetch(
            self,
            sources,
            media=("image", "sound", "text", "video"),
            keyword="",
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

        source_map = {"twitter": twitter}

        feature_collection = {
            "type": "FeatureCollection",
            "features": [],
        }
        if media and quantity > 0:
            for source in sources:
                source = source.lower()
                if source not in source_map:
                    raise ValueError('Source may be "Twitter".')
                for features in source_map[source](
                        keys=self.keychain[self.keyring[source]],
                        media=media,
                        keyword=keyword,
                        quantity=quantity,
                        location=location,
                        interval=interval,
                        **kwargs
                ):
                    feature_collection["features"].append(features)
        return feature_collection
