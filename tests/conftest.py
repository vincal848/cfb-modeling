import os

import pytest

from cfb.db import connect


@pytest.fixture
def db():
    conn = connect()
    yield conn
    conn.close()


def pytest_collection_modifyitems(config, items):
    if os.environ.get("CFBD_API_KEY"):
        return
    skip = pytest.mark.skip(reason="CFBD_API_KEY not set; live tests skipped")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
