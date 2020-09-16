
# coding: utf-8


import os
from setuptools import setup

import lspy


this_dir = os.path.dirname(os.path.abspath(__file__))

keywords = [
    "rpc", "json", "json-rpc", "2.0", "lsp"
]

classifiers = [
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Development Status :: 4 - Beta",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: BSD License",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Information Technology"
]

# read the readme file
with open(os.path.join(this_dir, "README.md"), "r") as f:
    long_description = f.read()


setup(
    name=lspy.__name__,
    version=lspy.__version__,
    author=lspy.__author__,
    author_email=lspy.__email__,
    description=lspy.__doc__.strip().split("\n")[0].strip(),
    license=lspy.__license__,
    url=lspy.__contact__,
    keywords=keywords,
    classifiers=classifiers,
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=2.7",
    zip_safe=False,
    py_modules=[lspy.__name__],
)
