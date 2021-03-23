"""Main module to orchestrate satellite image processes."""
from datetime import timedelta
from typing import Union

from prefect import Flow, Parameter, task
from prefect.executors import LocalDaskExecutor

from satflow.api import CopernicusApi, EarthExplorerApi

executor = LocalDaskExecutor(scheduler="threads", num_workers=8)


@task(max_retries=3, retry_delay=timedelta(seconds=5))
def query(
    product_type: str, bbox: list[float], start_date: str, end_date: str
) -> list[dict]:
    """Prefect Task implementing queries to providers returning available products."""
    api: Union[EarthExplorerApi, CopernicusApi]

    if product_type == 'S2MSI1C':
        api = CopernicusApi()
    elif product_type == 'landsat_8_c1':
        api = EarthExplorerApi()
    else:
        raise ValueError('Product type value is not currently supported.')

    results = api.query(
        product_type=product_type, bbox=bbox, start_date=start_date, end_date=end_date
    )

    return results


@task
def download_all(products: list[dict]) -> list[str]:
    """Prefect Task to download requested product."""
    api: Union[EarthExplorerApi, CopernicusApi]

    product_dirs = []
    for product in products:
        if 'uuid' in product:
            api = CopernicusApi()
            output_dir = '../satdata/sentinel'
        elif 'entity_id' in product:
            api = EarthExplorerApi()
            output_dir = '../satdata/landsat'
        else:
            raise ValueError('Unknown product type')
        product_dirs.append(api.download(product, output_dir))
    return product_dirs


with Flow("Sensor Harmonization Workflow", executor=executor) as flow:

    bbox = Parameter('bbox')
    start_date, end_date = Parameter('start_date'), Parameter('end_date')

    products_msi = query(
        product_type='S2MSI1C', bbox=bbox, start_date=start_date, end_date=end_date
    )

    products_oli = query(
        product_type='landsat_8_c1', bbox=bbox, start_date=start_date, end_date=end_date
    )

    product_msi_dirs = download_all(products_msi)
    product_oli_dirs = download_all(products_oli)

    parameters = dict(
        bbox=(23.5, 37.7, 24, 38.2), start_date=('20210112'), end_date=('20210114')
    )

    # state = flow.run(parameters=parameters)
flow.register(project_name="satellite_harmonization")
