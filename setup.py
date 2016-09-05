#!/usr/bin/env python3
# coding: utf-8

"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    README = readme_file.read()

setup(
    name="OGRe",
    version='4.6.0',
    description='OpenFusion GeoJSON Retriever',
    long_description=README,
    author='David Tucker',
    author_email='dmtucker@ucsc.edu',
    license='LGPLv2+',
    url='https://github.com/dmtucker/ogre',
    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    install_requires=[
        'twython ~= 3.4',
    ],
    entry_points={'console_scripts': ['ogre = ogre.cli:main']},
    keywords='OpenFusion Twitter GeoJSON geotag',
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 4 - Beta',
    ],
)
