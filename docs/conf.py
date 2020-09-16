# -*- coding: utf-8 -*-


import sys
import os
import shlex


sys.path.insert(0, os.path.abspath(".."))
import lspy


project = "lspy"
author = lspy.__author__
copyright = lspy.__copyright__
version = lspy.__version__
release = lspy.__version__


templates_path = ["_templates"]
html_static_path = ["_static"]
master_doc = "index"
source_suffix = ".rst"


exclude_patterns = []
pygments_style = "sphinx"
html_logo = "../logo.png"
html_theme = "alabaster"
html_sidebars = {"**": [
    "about.html",
    "localtoc.html",
    "searchbox.html"]
}
html_theme_options = {
    "github_user": "firststef",
    "github_repo": "lspy",
    "travis_button": True
}


extensions = [
    "sphinx.ext.autodoc"
]
