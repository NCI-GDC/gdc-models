import os
from setuptools import setup, find_packages

VERSION_FILE = 'VERSION'


def get_version():
    """Returns the current gdc model version"""
    current_dir = os.path.dirname(os.path.realpath(__file__))
    version_path = os.path.join(current_dir, VERSION_FILE)

    with open(version_path, 'r') as f:
        return f.read().strip()


# Blatant theft of: https://stackoverflow.com/questions/4519127/setuptools-package-data-folder-location/26533921#26533921
try:
    os.symlink('../es-models/', 'gdcmodels/data')
    setup(
        name='gdcmodels',
        version=get_version(),
        packages=find_packages(exclude=[
            "scripts", "*-models", "*.tests", "*.tests.*", "tests.*", "tests"]),
        install_requires=[
            'PyYAML',
            'elasticsearch'
        ],
        package_data={
            'gdcmodels': ['data/*/*.yaml']
        }
    )
except Exception as e:
    print e.message
finally:
    os.unlink('gdcmodels/data')
