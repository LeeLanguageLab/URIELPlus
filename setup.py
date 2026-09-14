from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="urielplus",
    version="1.3",
    author="Mason Shipton",
    author_email="masonshipton25@gmail.com",
    description="URIEL+: Knowledge base for natural language processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="CC-BY-SA-4.0",
    url="https://github.com/Masonshipton25/URIELPlus",
    project_urls={
        "Bug Tracker": "https://github.com/Masonshipton25/URIELPlus/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "numpy>=1.24",
        "pandas>=2.0",
    ],
    extras_require={
        "imputation": [
            "contexttimer>=0.3.3",
            "fancyimpute>=0.7.0",
            "joblib>=1.4.2",
            "scikit-learn>=1.5.1",
            "scipy>=1.14.1",
        ],
        "midaspy": [
            "contexttimer>=0.3.3; python_version < '3.11'",
            "joblib>=1.4.2; python_version < '3.11'",
            "numpy<=1.26.4; python_version < '3.11'",
            "scikit-learn>=1.5.1; python_version < '3.11'",
            "MIDASpy>=1.4.0,<2; python_version < '3.11'",
            "tensorflow>=2.11,<2.12; python_version < '3.11'",
            "tensorflow-addons>=0.19,<0.20; python_version < '3.11'",
        ]
    },
    packages=find_packages(),
    include_package_data=True,
    license_files=("LICENSE.txt", "THIRD_PARTY_NOTICES.md"),
    python_requires=">=3.10",
)
