from setuptools import setup

version = "0.1.0"

with open("./README.md") as fd:
    long_description = fd.read()

setup(
    name="ping-party",
    version=version,
    description=
    "Send and receive UDP packets to and from hosts",
    long_description=long_description,
    install_requires=[
    ],
    author="Lee Kamentsky",
    packages=["ping_party"],
    entry_points={ 'console_scripts': [
        "ping-party=ping_party.main:main"
    ]},
    url="https://github.com/LeeKamentsky/ping-party",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        'Programming Language :: Python :: 3.5'
    ]
)