#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Kyoukai documentation build configuration file, created by
# sphinx-quickstart on Fri Jul 22 15:11:32 2016.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

import guzzle_sphinx_theme

sys.path.insert(0, os.path.abspath('..'))

import kyoukai

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinxcontrib.asyncio',
    'sphinx_autodoc_typehints',
    'sphinx.ext.autosummary',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The encoding of source files.
#
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Kyoukai'
copyright = '2016-2017, Laura Dickinson'
author = 'Laura Dickinson'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = kyoukai.__version__
# The full version, including alpha/beta/rc tags.
release = kyoukai.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True


# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'manni'


# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# Autodoc and autosummary
# Autodoc
autosummary_generate = True

autoclass_content = 'both'  # include both class docstring and __init__
autodoc_default_flags = [
    # Make sure that any autodoc declarations show the right members
    'members',
    'inherited-members',
    'private-members',
    'show-inheritance',
]
# make autodoc look less... bad
autodoc_member_order = "bysource"


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme_path = guzzle_sphinx_theme.html_theme_path()
html_theme = 'guzzle_sphinx_theme'


# A shorter title for the navigation bar.  Default is the same as html_title.
#
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#
# html_logo = None

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# Output file base name for HTML help builder.
htmlhelp_basename = 'Kyoukaidoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {}
latex_documents = [
    (master_doc, 'Kyoukai.tex', 'Kyoukai Documentation',
     'Isaac Dickinson', 'manual'),
]
# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'kyoukai', 'Kyoukai Documentation',
     [author], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'Kyoukai', 'Kyoukai Documentation',
     author, 'Kyoukai', 'One line description of project.',
     'Miscellaneous'),
]


# Map to the documentation of Python 3's stdlib.
intersphinx_mapping = {'python': ('https://docs.python.org/3/', None),
                       'mako': ('http://docs.makotemplates.org/en/latest/', None),
                       'werkzeug': ('http://werkzeug.pocoo.org/docs/0.11/', None)}
