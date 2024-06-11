"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from arelle.Version import authorLabel, copyrightLabel


__pluginInfo__ = {
    'name': 'Inline XBRL Document Set',
    'version': '1.1',
    'description': "This plug-in adds a feature to read manifest files of inline XBRL document sets "
                    " and to save the embedded XBRL instance document.  "
                    "Support single target instance documents in a single document set.  ",
    'license': 'Apache-2',
    'author': authorLabel,
    'copyright': copyrightLabel,
}
