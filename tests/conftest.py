import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--run-expensive", action="store_true", default=False,
        help="run expensive tests"
    )
    parser.addoption(
        "--run-only-expensive", action="store_true", default=False,
        help="run only expensive tests"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "expensive: mark test as expensive to run")

def pytest_collection_modifyitems(config, items):
    run_expensive = config.getoption("--run-expensive")
    run_only_expensive = config.getoption("--run-only-expensive")

    # If run-only-expensive is specified, skip all non-expensive tests
    if run_only_expensive:
        skip_non_expensive = pytest.mark.skip(reason="only running expensive tests")
        for item in items:
            if "expensive" not in item.keywords:
                item.add_marker(skip_non_expensive)
    # Otherwise if run-expensive is not specified, skip expensive tests
    elif not run_expensive:
        skip_expensive = pytest.mark.skip(reason="need --run-expensive option to run")
        for item in items:
            if "expensive" in item.keywords:
                item.add_marker(skip_expensive)
