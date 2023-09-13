from setuptools import find_packages, setup

setup(
    name="gdcmodels",
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
    package_data={"gdcmodels": ["es-models/*/*.yaml"]},
    entry_points={"console_scripts": ["init_index=gdcmodels.init_index:main"]},
)
