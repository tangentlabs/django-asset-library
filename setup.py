#!/usr/bin/env python
#-*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='django-asset-library',
    version='0.1',
    url='https://github.com/tangentlabs/django-asset-library',
    author=u"Izidor Matušov",
    author_email="izidor.matusov@tangentsnowball.com",
    description="Asset library for Django projects",
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=["tests*", "sites*"]),
    install_requires=[
        'django>=1.5,<1.7',
        'sorl-thumbnail>=11',
        'django-model-utils>=1.4.0',
    ],
)
