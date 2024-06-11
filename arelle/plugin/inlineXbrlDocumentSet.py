"""
See COPYRIGHT.md for copyright information.

## Overview

The Inline XBRL Document Set (IXDS) plugin facilitates the handling of inline XBRL documents.
It allows for opening and extracting XBRL data from document sets, either defined as an Inline XBRL Document Set or in a
manifest file (such as JP FSA) that identifies inline XBRL documents.

## Key Features

- **XBRL Document Set Detection**: Detect and load iXBRL documents from a zip file or directory.
- **Target Document Selection**: Load one or more Target Documents from an Inline Document Set.
- **Extract XML Instance**: Extract and save XML Instance of a Target Document.
- **Command Line Support**: Detailed syntax for file and target selection.
- **GUI Interaction**: Selection dialog for loading inline documents and saving target documents.

## Usage Instructions

### Command Line Usage

- **Loading Inline XBRL Documents from a Zip File**:
  ```bash
  python arelleCmdLine.py --plugins inlineXbrlDocumentSet --file '[{"ixds": [{"file": "filing-documents.zip"}]}]'
  ```
  This command loads all inline XBRL documents within a zip file as an Inline XBRL Document Set.

- **Loading Inline XBRL Documents from a Directory**:
  ```bash
  python arelleCmdLine.py --plugins inlineXbrlDocumentSet --file '[{"ixds": [{"file": "filing-documents-directory"}]}]'
  ```
  This command loads all inline XBRL documents within a specified directory.

- **Loading with Default Target Document**:
  ```bash
  python arelleCmdLine.py --plugins inlineXbrlDocumentSet --file '[{"ixds": [{"file1": "document-1.html", "file2": "document-2.html"}]}]'
  ```
  Load two inline XBRL documents using the default Target Document.

- **Specifying a Different Target Document**:
  ```bash
  python arelleCmdLine.py --plugins inlineXbrlDocumentSet --file '[{"ixds": [{"file1": "document-1.html", "file2": "document-2.html"}], "ixdsTarget": "DKGAAP"}]'
  ```
  Load two inline XBRL documents using the `DKGAAP` Target Document.

- **Loading Multiple Document Sets**:
  ```bash
  python arelleCmdLine.py --plugins inlineXbrlDocumentSet --file '[{"ixds": [{"file": "filing-documents-1.zip"}]}, {"ixds": [{"file": "filing-documents-2.zip"}]}]'
  ```
  Load two separate Inline XBRL Document Sets.

- **Extracting and Saving XML Instance**:
  ```bash
  python arelleCmdLine.py --plugins inlineXbrlDocumentSet --file '[{"ixds": [{"file": "filing-documents.zip"}]}] --saveInstance'
  ```
  Extract and save the XML Instance of the default Target Document from an Inline XBRL Document Set.

### GUI Usage

- **Loading Inline Documents as an IXDS**:
  1. Navigate to the `File` menu.
  2. Select `Open File Inline Doc Set`.
  3. Command/Control select multiple files to load them as an Inline XBRL Document Set.

- **Extracting and Saving XML Instance**:
  1. Load the Inline XBRL Document Set.
  2. Navigate to `Tools` in the menu.
  3. Select `Save target document` to save the XML Instance.

## Additional Notes

- Windows users must escape quotes and backslashes within the JSON file parameter structure:
`.\\arelleCmdLine.exe --plugins inlineXbrlDocumentSet --file "[{""ixds"":[{""file"":""C:\\\\filing-documents.zip""}], ""ixdsTarget"":""DKGAAP""}]" --package "C:\\taxonomy-package.zip"`
- If a JSON structure is specified in the `--file` option without an `ixdsTarget`, the default target is assumed.
- To specify a non-default target in the absence of a JSON file argument, use the formula parameter `ixdsTarget`.
- For EDGAR style encoding of non-ASCII characters, use the `--encodeSavedXmlChars` argument.
- Extracted XML instance is saved to the same directory as the IXDS with the suffix `_extracted.xbrl`.
"""
from __future__ import annotations

from arelle import FileSource, ModelXbrl
from arelle.RuntimeOptions import RuntimeOptions
from arelle.ValidateDuplicateFacts import DeduplicationType
from arelle.inline import DEFAULT_TARGET, IXDS_SURROGATE, IXDS_DOC_SEPARATOR, MINIMUM_IXDS_DOC_COUNT, saveTargetDocument, _saveTargetInstanceOverriden
from arelle.inline.ModelInlineXbrlDocumentSet import ModelInlineXbrlDocumentSet
from arelle.inline.TargetChoiceDialog import TargetChoiceDialog

DialogURL = None # dynamically imported when first used
from arelle.CntlrCmdLine import filesourceEntrypointFiles
from arelle.FileSource import archiveFilenameParts, archiveFilenameSuffixes
from arelle.ModelDocument import ModelDocumentReference, Type, load, create, inlineIxdsDiscover
from arelle.PluginManager import pluginClassMethods
from arelle.UrlUtil import isHttpUrl
from arelle.Version import authorLabel, copyrightLabel
from arelle.XmlValidate import validate as xmlValidate
import os
import regex as re


def loadDTS(modelXbrl, modelIxdsDocument):
    for htmlElt in modelXbrl.ixdsHtmlElements:
        for ixRefElt in htmlElt.iterdescendants(tag=htmlElt.modelDocument.ixNStag + "references"):
            if ixRefElt.get("target") == modelXbrl.ixdsTarget:
                modelIxdsDocument.schemaLinkbaseRefsDiscover(ixRefElt)
                xmlValidate(modelXbrl, ixRefElt) # validate instance elements

# this loader is used for test cases of multi-ix doc sets
def inlineXbrlDocumentSetLoader(modelXbrl, normalizedUri, filepath, isEntry=False, namespace=None, **kwargs):
    if isEntry:
        try:
            if "entrypoint" in kwargs and "ixdsTarget" in kwargs["entrypoint"]:
                _target = kwargs["entrypoint"].get("ixdsTarget") # assume None if not specified in entrypoint
            elif "ixdsTarget" in kwargs: # passed from validate (multio test cases)
                _target = kwargs["ixdsTarget"]
            else:
                _target = modelXbrl.modelManager.formulaOptions.parameterValues["ixdsTarget"][1]
            modelXbrl.ixdsTarget = None if _target == DEFAULT_TARGET else _target or None
        except (KeyError, AttributeError, IndexError, TypeError):
            pass # set later in selectTargetDocument plugin method
    createIxdsDocset = False
    ixdocs = None
    if "ixdsHtmlElements" in kwargs: # loading supplemental modelXbrl with preloaded htmlElements
        createIxdsDocset = True
        ixdocs = []
        modelXbrl.ixdsDocUrls = []
        modelXbrl.ixdsHtmlElements = kwargs["ixdsHtmlElements"]
        for ixdsHtmlElement in modelXbrl.ixdsHtmlElements:
            modelDocument = ixdsHtmlElement.modelDocument
            ixdocs.append(modelDocument)
            modelXbrl.ixdsDocUrls.append(modelDocument.uri)
            modelXbrl.urlDocs[modelDocument.uri] = modelDocument
        docsetUrl = modelXbrl.uriDir + "/_IXDS"
    elif IXDS_SURROGATE in normalizedUri:
        createIxdsDocset = True
        modelXbrl.ixdsDocUrls = []
        schemeFixup = isHttpUrl(normalizedUri) # schemes after separator have // normalized to single /
        msUNCfixup = modelXbrl.modelManager.cntlr.isMSW and normalizedUri.startswith("\\\\") # path starts with double backslash \\
        if schemeFixup:
            defectiveScheme = normalizedUri.partition("://")[0] + ":/"
            fixupPosition = len(defectiveScheme)
        for i, url in enumerate(normalizedUri.split(IXDS_DOC_SEPARATOR)):
            if schemeFixup and url.startswith(defectiveScheme) and url[len(defectiveScheme)] != "/":
                url = url[:fixupPosition] + "/" + url[fixupPosition:]
            if i == 0:
                docsetUrl = url
            else:
                if msUNCfixup and not url.startswith("\\\\") and url.startswith("\\"):
                    url = "\\" + url
                modelXbrl.ixdsDocUrls.append(url)
    if createIxdsDocset:
        # create surrogate entry object for inline document set which references ix documents
        xml = ["<instances>\n"]
        for url in modelXbrl.ixdsDocUrls:
            xml.append("<instance>{}</instance>\n".format(url))
        xml.append("</instances>\n")
        ixdocset = create(modelXbrl, Type.INLINEXBRLDOCUMENTSET, docsetUrl, isEntry=True, initialXml="".join(xml))
        ixdocset.type = Type.INLINEXBRLDOCUMENTSET
        ixdocset.targetDocumentPreferredFilename = None # possibly no inline docs in this doc set
        for i, elt in enumerate(ixdocset.xmlRootElement.iter(tag="instance")):
            # load ix document
            if ixdocs:
                ixdoc = ixdocs[i]
            else:
                ixdoc = load(modelXbrl, elt.text, referringElement=elt, isDiscovered=True)
            if ixdoc is not None:
                if ixdoc.type == Type.INLINEXBRL:
                    # set reference to ix document in document set surrogate object
                    referencedDocument = ModelDocumentReference("inlineDocument", elt)
                    ixdocset.referencesDocument[ixdoc] = referencedDocument
                    ixdocset.ixNS = ixdoc.ixNS # set docset ixNS
                    if ixdocset.targetDocumentPreferredFilename is None:
                        ixdocset.targetDocumentPreferredFilename = os.path.splitext(ixdoc.uri)[0] + ".xbrl"
                    ixdoc.inDTS = True # behaves like an entry
                else:
                    modelXbrl.warning("arelle:nonIxdsDocument",
                                      _("Non-inline file is not loadable into an Inline XBRL Document Set."),
                                      modelObject=ixdoc)
        # correct uriDir to remove surrogate suffix
        if IXDS_SURROGATE in modelXbrl.uriDir:
            modelXbrl.uriDir = os.path.dirname(modelXbrl.uriDir.partition(IXDS_SURROGATE)[0])
        if hasattr(modelXbrl, "ixdsHtmlElements"): # has any inline root elements
            if ixdocs:
                loadDTS(modelXbrl, ixdocset)
                modelXbrl.isSupplementalIxdsTarget = True
            inlineIxdsDiscover(modelXbrl, ixdocset, bool(ixdocs)) # compile cross-document IXDS references
            return ixdocset
    return None


def identifyInlineXbrlDocumentSet(modelXbrl, rootNode, filepath):
    for manifestElt in rootNode.iter(tag="{http://disclosure.edinet-fsa.go.jp/2013/manifest}manifest"):
        # it's an edinet fsa manifest of an inline XBRL document set
        return (Type.INLINEXBRLDOCUMENTSET, ModelInlineXbrlDocumentSet, manifestElt)
    return None # not a document set

def discoverInlineXbrlDocumentSet(modelDocument, *args, **kwargs):
    if isinstance(modelDocument, ModelInlineXbrlDocumentSet):
        return modelDocument.discoverInlineXbrlDocumentSet()
    return False  # not discoverable by this plug-in

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

def saveTargetDocumentMenuEntender(cntlr, menu, *args, **kwargs):
    # Extend menu with an item for the savedts plugin
    menu.add_command(label="Save target document",
                     underline=0,
                     command=lambda: saveTargetDocument(cntlr, runInBackground=True) )

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


def commandLineXbrlRun(cntlr, options: RuntimeOptions, modelXbrl, *args, **kwargs):
    deduplicationTypeArg = getattr(options, "deduplicateIxbrlFacts", None)
    deduplicationType = None if deduplicationTypeArg is None else DeduplicationType(deduplicationTypeArg)
    # skip if another class handles saving (e.g., EdgarRenderer)
    if _saveTargetInstanceOverriden(deduplicationType):
        return
    # extend XBRL-loaded run processing for this option
    if getattr(options, "saveTargetInstance", False) or getattr(options, "saveTargetFiling", False):
        if cntlr.modelManager is None or cntlr.modelManager.modelXbrl is None or (
            cntlr.modelManager.modelXbrl.modelDocument.type not in (Type.INLINEXBRL, Type.INLINEXBRLDOCUMENTSET)):
            cntlr.addToLog("No inline XBRL document or manifest loaded.")
            return
        saveTargetDocument(cntlr,
                                         runInBackground=False,
                                         saveTargetFiling=getattr(options, "saveTargetFiling", False),
                                         encodeSavedXmlChars=getattr(options, "encodeSavedXmlChars", False),
                                         xbrliNamespacePrefix=getattr(options, "xbrliNamespacePrefix"),
                                         deduplicationType=deduplicationType)


def discoverIxdsDts(modelXbrl):
    return hasattr(modelXbrl, "ixdsTarget") # if no target specified, block ixds discovery until all IX docs are loaded

def ixdsTargets(ixdsHtmlElements):
    return sorted(set(elt.get("target", DEFAULT_TARGET)
                              for htmlElt in ixdsHtmlElements
                              for elt in htmlElt.iterfind(f".//{{{htmlElt.modelDocument.ixNS}}}references")))

def selectTargetDocument(modelXbrl, modelIxdsDocument):
    if not hasattr(modelXbrl, "ixdsTarget"): # DTS discoverey deferred until all ix docs loaded
        # isolate any documents to separate IXDSes according to authority submission rules
        modelXbrl.targetIXDSesToLoad = [] # [[target,[ixdsHtmlElements], ...]
        for pluginXbrlMethod in pluginClassMethods('InlineDocumentSet.IsolateSeparateIXDSes'):
            separateIXDSesHtmlElements = pluginXbrlMethod(modelXbrl)
            if len(separateIXDSesHtmlElements) > 1: # [[ixdsHtml1, ixdsHtml2], [ixdsHtml3...] ...]
                for separateIXDSHtmlElements in separateIXDSesHtmlElements[1:]:
                    toLoadIXDS = [ixdsTargets(separateIXDSHtmlElements),[]]
                    modelXbrl.targetIXDSesToLoad.append(toLoadIXDS)
                    for ixdsHtmlElement in separateIXDSHtmlElements:
                        modelDoc = ixdsHtmlElement.modelDocument
                        toLoadIXDS[1].append(ixdsHtmlElement)
                        modelXbrl.ixdsHtmlElements.remove(ixdsHtmlElement)
                        del modelXbrl.urlDocs[modelDoc.uri]
                        if modelDoc in modelIxdsDocument.referencesDocument:
                            del modelIxdsDocument.referencesDocument[modelDoc]
                # the primary target  instance may have changed
                modelIxdsDocument.targetDocumentPreferredFilename = os.path.splitext(modelXbrl.ixdsHtmlElements[0].modelDocument.uri)[0] + ".xbrl"
        # find target attributes
        _targets = ixdsTargets(modelXbrl.ixdsHtmlElements)
        if len(_targets) == 0:
            _target = DEFAULT_TARGET
        elif len(_targets) == 1:
            _target = _targets[0]
        elif modelXbrl.modelManager.cntlr.hasGui:
            if True: # provide option to load all or ask user which target
                modelXbrl.targetIXDSesToLoad.insert(0, [_targets[1:],modelXbrl.ixdsHtmlElements])
                _target = _targets[0]
            else: # ask user which target
                dlg = TargetChoiceDialog(modelXbrl.modelManager.cntlr.parent, _targets)
                _target = dlg.selection
        else:
            # load all targets (supplemental are accessed from first via modelXbrl.loadedModelXbrls)
            modelXbrl.targetIXDSesToLoad.insert(0, [_targets[1:],modelXbrl.ixdsHtmlElements])
            _target = _targets[0]
            #modelXbrl.warning("arelle:unspecifiedTargetDocument",
            #                  _("Target document not specified, loading %(target)s, found targets %(targets)s"),
            #                  modelObject=modelXbrl, target=_target, targets=_targets)
        modelXbrl.ixdsTarget = None if _target == DEFAULT_TARGET else _target or None
        # load referenced schemas and linkbases (before validating inline HTML
        loadDTS(modelXbrl, modelIxdsDocument)
    # now that all ixds doc(s) references loaded, validate resource elements
    for htmlElt in modelXbrl.ixdsHtmlElements:
        for inlineElement in htmlElt.iterdescendants(tag=htmlElt.modelDocument.ixNStag + "resources"):
            xmlValidate(modelXbrl, inlineElement) # validate instance elements

def ixdsTargetDiscoveryCompleted(modelXbrl, modelIxdsDocument):
    targetIXDSesToLoad = getattr(modelXbrl, "targetIXDSesToLoad", False)
    if targetIXDSesToLoad:
        # load and discover additional targets
        modelXbrl.supplementalModelXbrls = []
        for targets, ixdsHtmlElements in targetIXDSesToLoad:
            for target in targets:
                modelXbrl.supplementalModelXbrls.append(
                    ModelXbrl.load(modelXbrl.modelManager, ixdsHtmlElements[0].modelDocument.uri,
                                   f"loading secondary target {target} {ixdsHtmlElements[0].modelDocument.uri}",
                                   useFileSource=modelXbrl.fileSource, ixdsTarget=target, ixdsHtmlElements=ixdsHtmlElements)
                )
        modelXbrl.modelManager.loadedModelXbrls.extend(modelXbrl.supplementalModelXbrls)
    # provide schema references for IXDS document
    modelIxdsDocument.targetDocumentSchemaRefs = set()  # union all the instance schemaRefs
    for referencedDoc in modelIxdsDocument.referencesDocument.keys():
        if referencedDoc.type == Type.SCHEMA:
            modelIxdsDocument.targetDocumentSchemaRefs.add(modelIxdsDocument.relativeUri(referencedDoc.uri))

__pluginInfo__ = {
    'name': 'Inline XBRL Document Set',
    'version': '1.1',
    'description': "This plug-in adds a feature to read manifest files of inline XBRL document sets "
                    " and to save the embedded XBRL instance document.  "
                    "Support single target instance documents in a single document set.  ",
    'license': 'Apache-2',
    'author': authorLabel,
    'copyright': copyrightLabel,
    # classes of mount points (required)
    'CntlrWinMain.Menu.File.Open': fileOpenMenuEntender,
    'CntlrWinMain.Menu.Tools': saveTargetDocumentMenuEntender,
    'CntlrCmdLine.Xbrl.Run': commandLineXbrlRun,
    'ModelDocument.PullLoader': inlineXbrlDocumentSetLoader,
    'ModelDocument.IdentifyType': identifyInlineXbrlDocumentSet,
    'ModelDocument.Discover': discoverInlineXbrlDocumentSet,
    'ModelDocument.DiscoverIxdsDts': discoverIxdsDts,
    'ModelDocument.SelectIxdsTarget': selectTargetDocument,
    'ModelDocument.IxdsTargetDiscovered': ixdsTargetDiscoveryCompleted,
}
