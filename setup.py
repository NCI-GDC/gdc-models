from setuptools import setup, find_packages


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
        "six~=1.15",
    ],
    # package_data={
    #     "gdcmodels": ["es-models/*/*.yaml"]
    # },
    entry_points={
        "console_scripts": ["init_index=gdcmodels.init_index:main"]
    },
    zip_safe=True,
)
