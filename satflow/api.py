"""Functions to download satellite images."""
import os

import prefect
from landsatxplore.api import API
from landsatxplore.earthexplorer import EarthExplorer
from sentinelsat import SentinelAPI
from shapely.geometry import MultiPoint

logging = prefect.context.get("logger")


class ProviderApi:
    """Template for Satellite Provider API classes to connect to a provider with functionality to
    query and download products."""

    def query(
        self, product_type: str, bbox: list[float], start_date: str, end_date: str
    ) -> list[dict]:
        """Describes how to query requested product results based on given criteria."""
        raise NotImplementedError(
            "Query method not implemented on current provider API."
        )

    def download(self, product, output_dir):
        """Describes how to download requested products."""
        raise NotImplementedError(
            "Download method not implemented on current provider API."
        )


class EarthExplorerApi(ProviderApi):
    """USGS Earth Explorer API to download supported satellite image products."""

    def __init__(self):
        """
        Loads username/password from env vars and connects to USGS API.

        WARNING: Needs LANDSATXPLORE_USERNAME and LANDSATXPLORE_PASSWORD environment vars
        to connect to USGS Earth Explorer API.
        """

        # Load env variables with user, pass info
        self.username = os.getenv('LANDSATXPLORE_USERNAME')
        self.password = os.getenv('LANDSATXPLORE_PASSWORD')

        assert (
            self.username and self.password
        ), 'Essential environment variables have not been set.'

    def query(
        self, product_type: str, bbox: list[float], start_date: str, end_date: str
    ) -> list[dict]:
        """Search for products based on given criteria supported by the provider."""
        # Initialize a new API instance and get an access key
        query_api = API(self.username, self.password)

        products = query_api.search(
            dataset=product_type,
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
        )

        logging.info('Landsat query found %s products.', len(products))

        query_api.logout()

        return products

    def download(self, product: dict, output_dir: str) -> str:
        """Download landsat satellite images from USGS Earth Explorer Platform."""
        download_api = EarthExplorer(self.username, self.password)

        logging.info('Requested Landsat product %s', product['entity_id'])
        file_dir = download_api.download(product['entity_id'], output_dir=output_dir)

        download_api.logout()

        return file_dir


class CopernicusApi(ProviderApi):
    """Copernicus SciHub API to download supported Sentinel image products."""

    def __init__(self):
        """
        Loads username/password from env vars and connects to Copernicus SciHub API.

        WARNING: Needs DHUS_USER and DHUS_PASSWORD environment vars
        to connect to Copernicus OpenHub API.
        """
        # Load env variables with user, pass info
        username = os.getenv('DHUS_USER')
        password = os.getenv('DHUS_PASSWORD')
        assert (
            username and password
        ), 'Essential username/password environment variables have not been set.'

        # Initialize a new API instance
        self.api = SentinelAPI(username, password, 'https://scihub.copernicus.eu/dhus')

    def query(
        self, product_type: str, bbox: list[float], start_date: str, end_date: str
    ) -> list[dict]:
        """Search for products based on given criteria supported by the provider."""
        products = self.api.query(
            self.bbox_to_wkt(bbox),
            date=(start_date, end_date),
            producttype=product_type,
        )

        logging.info('Sentinel query found %s scenes.', len(products))

        return self.ordered_dict_to_list(products)

    def download(self, product: dict, output_dir: str) -> str:
        """Download copernicus satellite images from Copernicus Platform."""
        logging.info('Requested Sentinel product %s', product['title'])

        file_dir = self.api.download(product['uuid'], directory_path=output_dir)

        return file_dir

    @staticmethod
    def bbox_to_wkt(bbox: list[float]) -> str:
        """Transform bbox to wkt object."""
        return MultiPoint([(bbox[0], bbox[2]), (bbox[1], bbox[3])]).wkt

    @staticmethod
    def ordered_dict_to_list(ordered_dict: dict) -> list[dict]:
        """Transform ordered dictionary to list, by dropping dictionary keys"""
        return list(ordered_dict.values())
