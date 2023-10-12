from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="gdcmodels",
    description="Stores and serves GDC data models defined in static YAML files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="NCI GDC",
    author_email="gdc_dev_questions-aaaaae2lhsbell56tlvh3upgoq@cdis.slack.com",
    url="https://github.com/NCI-GDC/gdcdatamodel",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    license="Apache",
    setup_requires=["setuptools_scm<6"],
    use_scm_version={"local_scheme": "dirty-tag", "fallback_version": "local"},
    packages=find_packages(
        exclude=["scripts", "*-models", "*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    install_requires=[
        "PyYAML>=3.11,<6",
        "elasticsearch>=7.0.0,<8.0.0",
        "deepdiff~=6.5.0",
        "mergedeep~=1.3.4",
    ],
    python_requires=">=3.7",
    package_data={"gdcmodels": ["es-models/*/*.yaml"]},
    entry_points={"console_scripts": ["init_index=gdcmodels.init_index:main"]},
)
