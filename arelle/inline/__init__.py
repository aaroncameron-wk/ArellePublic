"""
See COPYRIGHT.md for copyright information.
"""
import os
from collections import defaultdict
from optparse import SUPPRESS_HELP
from typing import Type

from arelle import ValidateDuplicateFacts, FileSource
from arelle.ModelObject import ModelObject

DEFAULT_TARGET = "(default)"
IXDS_SURROGATE = "_IXDS#?#"  # surrogate (fake) file name for inline XBRL doc set (IXDS)
IXDS_DOC_SEPARATOR = "#?#"  # the files of the document set follow the above "surrogate" with these separators
MINIMUM_IXDS_DOC_COUNT = 2  # make this 2 to cause single-documents to be processed without a document set object

_skipExpectedInstanceComparison = None


def addInlineCommandLineOptions(parser):
    # extend command line options with a save DTS option
    parser.add_option("--saveInstance",
                      action="store_true",
                      dest="saveTargetInstance",
                      help=_("Save target instance document"))
    parser.add_option("--saveinstance",  # for WEB SERVICE use
                      action="store_true",
                      dest="saveTargetInstance",
                      help=SUPPRESS_HELP)
    parser.add_option("--saveFiling",
                      action="store",
                      dest="saveTargetFiling",
                      help=_("Save instance and DTS in zip"))
    parser.add_option("--savefiling",  # for WEB SERVICE use
                      action="store",
                      dest="saveTargetFiling",
                      help=SUPPRESS_HELP)
    parser.add_option("--skipExpectedInstanceComparison",
                      action="store_true",
                      dest="skipExpectedInstanceComparison",
                      help=_("Skip inline XBRL testcases from comparing expected result instances"))
    parser.add_option("--encodeSavedXmlChars",
                      action="store_true",
                      dest="encodeSavedXmlChars",
                      help=_("Encode saved xml characters (&#x80; and above)"))
    parser.add_option("--encodesavedxmlchars",  # for WEB SERVICE use
                      action="store_true",
                      dest="encodeSavedXmlChars",
                      help=SUPPRESS_HELP)
    parser.add_option("--xbrliNamespacePrefix",
                      action="store",
                      dest="xbrliNamespacePrefix",
                      help=_("The namespace prefix to use for http://www.xbrl.org/2003/instance. It's used as the default namespace when unset."),
                      type="string")
    parser.add_option("--xbrlinamespaceprefix",  # for WEB SERVICE use
                      action="store",
                      dest="xbrliNamespacePrefix",
                      help=SUPPRESS_HELP,
                      type="string")
    parser.add_option("--deduplicateIxbrlFacts",
                      action="store",
                      choices=[a.value for a in ValidateDuplicateFacts.DeduplicationType],
                      dest="deduplicateIxbrlFacts",
                      help=_("Remove duplicate facts when extracting XBRL instance."))
    parser.add_option("--deduplicateixbrlfacts",  # for WEB SERVICE use
                      action="store",
                      choices=[a.value for a in ValidateDuplicateFacts.DeduplicationType],
                      dest="deduplicateIxbrlFacts",
                      help=SUPPRESS_HELP)


def getInlineReadMeFirstUris(modelTestcaseVariation):
    _readMeFirstUris = [os.path.join(modelTestcaseVariation.modelDocument.filepathdir,
                                     (elt.get("{http://www.w3.org/1999/xlink}href") or elt.text).strip())
                        for elt in modelTestcaseVariation.iterdescendants()
                        if isinstance(elt,ModelObject) and elt.get("readMeFirst") == "true"]
    if len(_readMeFirstUris) >= MINIMUM_IXDS_DOC_COUNT and all(
            Type.identify(modelTestcaseVariation.modelXbrl.fileSource, f) == Type.INLINEXBRL for f in _readMeFirstUris):
        docsetSurrogatePath = os.path.join(os.path.dirname(_readMeFirstUris[0]), IXDS_SURROGATE)
        modelTestcaseVariation._readMeFirstUris = [docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(_readMeFirstUris)]
        return True


def getReportPackageIxds(filesource, lookOutsideReportsDirectory=False, combineIntoSingleIxds=False):
    # single report directory
    reportFiles = []
    ixdsDirFiles = defaultdict(list)
    reportDir = "*uninitialized*"
    reportDirLen = 0
    for f in filesource.dir:
        if f.endswith("/reports/") and reportDir == "*uninitialized*":
            reportDir = f
            reportDirLen = len(f)
        elif f.startswith(reportDir):
            if "/" not in f[reportDirLen:]:
                filesource.select(f)
                if Type.identify(filesource, filesource.url) in (Type.INSTANCE, Type.INLINEXBRL):
                    reportFiles.append(f)
            else:
                ixdsDir, _sep, ixdsFile = f.rpartition("/")
                if ixdsFile:
                    filesource.select(f)
                    if Type.identify(filesource, filesource.url) == Type.INLINEXBRL:
                        ixdsDirFiles[ixdsDir].append(f)
    if lookOutsideReportsDirectory:
        for f in filesource.dir:
            filesource.select(f)
            if Type.identify(filesource, filesource.url) in (Type.INSTANCE, Type.INLINEXBRL):
                reportFiles.append(f)
    if combineIntoSingleIxds and (reportFiles or len(ixdsDirFiles) > 1):
        docsetSurrogatePath = os.path.join(filesource.baseurl, IXDS_SURROGATE)
        for ixdsFiles in ixdsDirFiles.values():
            reportFiles.extend(ixdsFiles)
        return docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(os.path.join(filesource.baseurl,f) for f in reportFiles)
    for ixdsDir, ixdsFiles in sorted(ixdsDirFiles.items()):
        # use the first ixds in report package
        docsetSurrogatePath = os.path.join(filesource.baseurl, ixdsDir, IXDS_SURROGATE)
        return docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(os.path.join(filesource.baseurl,f) for f in ixdsFiles)
    for f in reportFiles:
        filesource.select(f)
        if Type.identify(filesource, filesource.url) in (Type.INSTANCE, Type.INLINEXBRL):
            # return the first inline doc
            return f
    return None


def prepareInlineEntrypointFiles(cntlr, options, entrypointFiles):
    global _skipExpectedInstanceComparison
    _skipExpectedInstanceComparison = getattr(options, "skipExpectedInstanceComparison", False)
    if isinstance(entrypointFiles, list):
        # check for any inlineDocumentSet in list
        for entrypointFile in entrypointFiles:
            _ixds = entrypointFile.get("ixds")
            if isinstance(_ixds, list):
                # build file surrogate for inline document set
                _files = [e["file"] for e in _ixds if isinstance(e, dict)]
                if len(_files) == 1:
                    urlsByType = {}
                    if os.path.isfile(_files[0]) and any(_files[0].endswith(e) for e in (".zip", ".ZIP", ".tar.gz" )): # check if an archive file
                        filesource = FileSource.openFileSource(_files[0], cntlr)
                        if filesource.isArchive:
                            for _archiveFile in (filesource.dir or ()): # .dir might be none if IOerror
                                filesource.select(_archiveFile)
                                identifiedType = Type.identify(filesource, filesource.url)
                                if identifiedType in (Type.INSTANCE, Type.INLINEXBRL):
                                    urlsByType.setdefault(identifiedType, []).append(filesource.url)
                        filesource.close()
                    elif os.path.isdir(_files[0]):
                        _fileDir = _files[0]
                        for _localName in os.listdir(_fileDir):
                            _file = os.path.join(_fileDir, _localName)
                            if os.path.isfile(_file):
                                filesource = FileSource.openFileSource(_file, cntlr)
                                identifiedType = Type.identify(filesource, filesource.url)
                                if identifiedType in (Type.INSTANCE, Type.INLINEXBRL):
                                    urlsByType.setdefault(identifiedType, []).append(filesource.url)
                                filesource.close()
                    if urlsByType:
                        _files = []
                        # use inline instances, if any, else non-inline instances
                        for identifiedType in (Type.INLINEXBRL, Type.INSTANCE):
                            for url in urlsByType.get(identifiedType, []):
                                _files.append(url)
                            if _files:
                                break # found inline (or non-inline) entrypoint files, don't look for any other type
                if len(_files) > 0:
                    docsetSurrogatePath = os.path.join(os.path.dirname(_files[0]), IXDS_SURROGATE)
                    entrypointFile["file"] = docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(_files)


def skipExpectedInstanceComparison():
    global _skipExpectedInstanceComparison
    return bool(_skipExpectedInstanceComparison)
