from setuptools import setup, find_packages


setup(
    name='gdcmodels',
    version='1.0.0',
    packages=find_packages(exclude=[
        "scripts", "*-models", "*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=[
        'PyYAML>=3.11,<6',
        'elasticsearch>=5.0.0,<6.0.0'
    ],
    package_data={
        'gdcmodels': ['es-models/*/*.yaml'],
    },
)
