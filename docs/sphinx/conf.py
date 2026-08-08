# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'corpus-tools'
copyright = '2024, Randy True'
author = 'Randy True'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
# html_static_path = ['_static']  # was giving warning so commented out

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    # other extensions...
]

napoleon_custom_sections = [('category', 'params_style'), ('heading', 'params_style'), ('usage', 'params_style')]

import os
import sys
sys.path.insert(0, os.path.abspath('../general'))

# CLI line
#sphinx-build -b html docs docs/_build/html
