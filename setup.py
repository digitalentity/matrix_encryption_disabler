#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(name="matrix-e2ee-filter",
      version="1.0.0",
      packages=setuptools.find_packages(),
      description="Encrypted room filter module for Synapse",
      long_description=long_description,
      long_description_content_type="text/markdown",
      author="Konstantin Sharlaimov",
      author_email="konstantin.sharlaimov@gmail.com",
      license="MPL",
      install_requires=["matrix-synapse"],
      url="https://github.com/digitalentity/matrix_encryption_disabler",
      project_urls={
        "Bug Tracker": "https://github.com/digitalentity/matrix_encryption_disabler/issues",
      },
      classifiers=[],
      python_requires=">=3.6",
    )