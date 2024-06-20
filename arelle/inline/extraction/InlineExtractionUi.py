"""
See COPYRIGHT.md for copyright information.
"""
from arelle.inline.extraction.InlineExtraction import saveTargetDocument


def saveTargetDocumentMenuEntender(cntlr, menu):
    # Extend menu with an item for the savedts plugin
    menu.add_command(label="Save target document",
                     underline=0,
                     command=lambda: saveTargetDocument(cntlr, runInBackground=True) )
