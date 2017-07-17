import os
from setuptools import setup, find_packages

VERSION_FILE = 'VERSION'


def get_version():
    """Returns the current gdc model version"""
    current_dir = os.path.dirname(os.path.realpath(__file__))
    version_path = os.path.join(current_dir, VERSION_FILE)

    with open(version_path, 'r') as f:
        return f.read().strip()


setup(
    name = 'gdcmodels',
    version = get_version(),
    packages = find_packages(exclude=[
        "scripts", "*-models", "*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires = [
        'PyYAML',
        'elasticsearch'
    ],
    package_data = {
        'gdcmodels': ['es-models/*/*.yaml']
    }
)
