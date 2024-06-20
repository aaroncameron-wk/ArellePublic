"""
See COPYRIGHT.md for copyright information.
"""
import os

import regex as re

from arelle import FileSource
from arelle.CntlrCmdLine import filesourceEntrypointFiles
from arelle.FileSource import archiveFilenameSuffixes, archiveFilenameParts
from arelle.inline.InlineConstants import IXDS_SURROGATE, IXDS_DOC_SEPARATOR, MINIMUM_IXDS_DOC_COUNT

DialogURL = None  # dynamically imported when first used


def fileOpenMenuEntender(cntlr, menu, *args, **kwargs):
    # install DialogURL for GUI menu operation of runOpenWebInlineDocumentSetMenuCommand
    global DialogURL
    from arelle import DialogURL
    # Extend menu with an item for the savedts plugin
    menu.insert_command(2, label="Open Web Inline Doc Set",
                        underline=0,
                        command=lambda: runOpenWebInlineDocumentSetMenuCommand(cntlr, runInBackground=True) )
    menu.insert_command(2, label="Open File Inline Doc Set",
                        underline=0,
                        command=lambda: runOpenFileInlineDocumentSetMenuCommand(cntlr, runInBackground=True) )


def runOpenFileInlineDocumentSetMenuCommand(cntlr, runInBackground=False, saveTargetFiling=False):
    filenames = cntlr.uiFileDialog("open",
                                   multiple=True,
                                   title=_("arelle - Multi-open inline XBRL file(s)"),
                                   initialdir=cntlr.config.setdefault("fileOpenDir","."),
                                   filetypes=[(_("XBRL files"), "*.*")],
                                   defaultextension=".xbrl")
    runOpenInlineDocumentSetMenuCommand(cntlr, filenames, runInBackground, saveTargetFiling)


def runOpenWebInlineDocumentSetMenuCommand(cntlr, runInBackground=False, saveTargetFiling=False):
    url = DialogURL.askURL(cntlr.parent, buttonSEC=True, buttonRSS=True)
    if url:
        runOpenInlineDocumentSetMenuCommand(cntlr, re.split(r",\s*|\s+", url), runInBackground, saveTargetFiling)


def runOpenInlineDocumentSetMenuCommand(cntlr, filenames, runInBackground=False, saveTargetFiling=False):
    if os.sep == "\\":
        filenames = [f.replace("/", "\\") for f in filenames]

    if not filenames:
        filename = ""
    elif len(filenames) == 1 and any(filenames[0].endswith(s) for s in archiveFilenameSuffixes):
        # get archive file names
        from arelle.FileSource import openFileSource
        filesource = openFileSource(filenames[0], cntlr)
        if filesource.isArchive:
            # identify entrypoint files
            try:
                entrypointFiles = filesourceEntrypointFiles(filesource, inlineOnly=True)
                l = len(filesource.baseurl) + 1 # len of the base URL of the archive
                selectFiles = [e["file"][l:] for e in entrypointFiles if "file" in e] + \
                              [e["file"][l:] for i in entrypointFiles if "ixds" in i for e in i["ixds"] if "file" in e]
            except FileSource.ArchiveFileIOError:
                selectFiles = None
            from arelle import DialogOpenArchive
            archiveEntries = DialogOpenArchive.askArchiveFile(cntlr, filesource, multiselect=True, selectFiles=selectFiles)
            if archiveEntries:
                ixdsFirstFile = archiveEntries[0]
                _archiveFilenameParts = archiveFilenameParts(ixdsFirstFile)
                if _archiveFilenameParts is not None:
                    ixdsDir = _archiveFilenameParts[0] # it's a zip or package, use zip file name as head of ixds
                else:
                    ixdsDir = os.path.dirname(ixdsFirstFile)
                docsetSurrogatePath = os.path.join(ixdsDir, IXDS_SURROGATE)
                filename = docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(archiveEntries)
            else:
                filename = None
        else:
            filename = None
        filesource.close()
    elif len(filenames) >= MINIMUM_IXDS_DOC_COUNT:
        ixdsFirstFile = filenames[0]
        _archiveFilenameParts = archiveFilenameParts(ixdsFirstFile)
        if _archiveFilenameParts is not None:
            ixdsDir = _archiveFilenameParts[0] # it's a zip or package, use zip file name as head of ixds
        else:
            ixdsDir = os.path.dirname(ixdsFirstFile)
        docsetSurrogatePath = os.path.join(ixdsDir, IXDS_SURROGATE)
        filename = docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(filenames)
    else:
        filename = filenames[0]
    if filename is not None:
        cntlr.fileOpenFile(filename)
