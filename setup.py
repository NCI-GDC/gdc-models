from setuptools import setup, find_packages


setup(
    name="gdcmodels",
    setup_requires=["setuptools_scm"],
    use_scm_version={"local_scheme": "dirty-tag"},
    packages=find_packages(
        exclude=["scripts", "*-models", "*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    install_requires=[
        "PyYAML>=3.11,<6",
        "elasticsearch>=5.0.0,<6.0.0",
    ],
    package_data={
        "gdcmodels": ["es-models/*/*.yaml"]
    },
)
