from setuptools import setup
import re
import os

_version_re = re.compile(r"(?<=^__version__ = (\"|'))(.+)(?=\"|')")

def get_version(rel_path: str) -> str:
    """
    Searches for the ``__version__ = `` line in a source code file.

    https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
    """
    with open(rel_path, 'r') as f:
        matches = map(_version_re.search, f)
        filtered = filter(lambda m: m is not None, matches)
        version = next(filtered, None)
        if version is None:
            raise RuntimeError(f'Could not find __version__ in {rel_path}')
        return version.group(0)


setup(
    name                = 'dylld',
    version             = get_version('dylld.py'),
    description         = 'A ChRIS plugin that dynamically builds a workflow to compute length discrepencies from extremity X-Rays',
    author              = 'FNNDSC',
    author_email        = 'rudolph.pienaar@childrens.harvard.edu',
    url                 = 'https://github.com/rudolphpienaar/pl-dylld',
    py_modules          = ['dylld'],
    install_requires    = ['chris_plugin', 'pflogf', 'pudb'],
    packages            =  ['control', 'logic', 'state'],
    license             = 'MIT',
    entry_points        = {
        'console_scripts': [
            'dylld = dylld:main'
        ]
    },
    classifiers         =[
        'License :: OSI Approved :: MIT License',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.'
    ],
    extras_require      ={
        'none': [],
        'dev': [
            'pytest~=7.1',
            'pytest-mock~=3.8'
        ]
    }
)
