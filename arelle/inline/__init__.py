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
import os
import zipfile
from collections import defaultdict
from optparse import SUPPRESS_HELP
from typing import Type

from lxml.etree import XML, XMLSyntaxError

from arelle import ValidateDuplicateFacts, FileSource, ModelXbrl, ValidateXbrlDimensions, XbrlConst
from arelle.ModelInstanceObject import ModelInlineFootnote
from arelle.ModelObject import ModelObject
from arelle.ModelValue import INVALIDixVALUE, qname
from arelle.PluginManager import pluginClassMethods
from arelle.PrototypeDtsObject import LocPrototype, ArcPrototype
from arelle.RuntimeOptions import RuntimeOptions
from arelle.UrlUtil import isHttpUrl
from arelle.ValidateDuplicateFacts import DeduplicationType
from arelle.ValidateFilingText import CDATApattern
from arelle.XmlUtil import xmlnsprefix, addChild, setXmlns, elementFragmentIdentifier, copyIxFootnoteHtml
from arelle.XmlValidate import VALID, NONE
from arelle.XmlValidate import validate as xmlValidate


DEFAULT_TARGET = "(default)"
IXDS_SURROGATE = "_IXDS#?#"  # surrogate (fake) file name for inline XBRL doc set (IXDS)
IXDS_DOC_SEPARATOR = "#?#"  # the files of the document set follow the above "surrogate" with these separators
MINIMUM_IXDS_DOC_COUNT = 2  # make this 2 to cause single-documents to be processed without a document set object

_skipExpectedInstanceComparison = None


# baseXmlLang: set on root xbrli:xbrl element
# defaultXmlLang: if a fact/footnote has a different lang, provide xml:lang on it.
def createTargetInstance(
        modelXbrl,
        targetUrl,
        targetDocumentSchemaRefs,
        filingFiles,
        baseXmlLang=None,
        defaultXmlLang=None,
        skipInvalid=False,
        xbrliNamespacePrefix=None,
        deduplicationType: ValidateDuplicateFacts.DeduplicationType | None = None):
    def addLocallyReferencedFile(elt,filingFiles):
        if elt.tag in ("a", "img"):
            for attrTag, attrValue in elt.items():
                if attrTag in ("href", "src") and not isHttpUrl(attrValue) and not os.path.isabs(attrValue):
                    attrValue = attrValue.partition('#')[0] # remove anchor
                    if attrValue: # ignore anchor references to base document
                        attrValue = os.path.normpath(attrValue) # change url path separators to host separators
                        file = os.path.join(sourceDir,attrValue)
                        if modelXbrl.fileSource.isInArchive(file, checkExistence=True) or os.path.exists(file):
                            filingFiles.add(file)
    targetInstance = ModelXbrl.create(modelXbrl.modelManager,
                                      newDocumentType=Type.INSTANCE,
                                      url=targetUrl,
                                      schemaRefs=targetDocumentSchemaRefs,
                                      isEntry=True,
                                      discover=False,  # don't attempt to load DTS
                                      xbrliNamespacePrefix=xbrliNamespacePrefix)
    ixTargetRootElt = modelXbrl.ixTargetRootElements[getattr(modelXbrl, "ixdsTarget", None)]
    langIsSet = False
    # copy ix resources target root attributes
    for attrName, attrValue in ixTargetRootElt.items():
        if attrName != "target": # ix:references target is not mapped to xbrli:xbrl
            targetInstance.modelDocument.xmlRootElement.set(attrName, attrValue)
        if attrName == "{http://www.w3.org/XML/1998/namespace}lang":
            langIsSet = True
            defaultXmlLang = attrValue
        if attrName.startswith("{"):
            ns, _sep, ln = attrName[1:].rpartition("}")
            if ns:
                prefix = xmlnsprefix(ixTargetRootElt, ns)
                if prefix not in (None, "xml"):
                    setXmlns(targetInstance.modelDocument, prefix, ns)

    if not langIsSet and baseXmlLang:
        targetInstance.modelDocument.xmlRootElement.set("{http://www.w3.org/XML/1998/namespace}lang", baseXmlLang)
        if defaultXmlLang is None:
            defaultXmlLang = baseXmlLang # allows facts/footnotes to override baseXmlLang
    ValidateXbrlDimensions.loadDimensionDefaults(targetInstance) # need dimension defaults
    # roleRef and arcroleRef (of each inline document)
    for sourceRefs in (modelXbrl.targetRoleRefs, modelXbrl.targetArcroleRefs):
        for roleRefElt in sourceRefs.values():
            addChild(targetInstance.modelDocument.xmlRootElement, roleRefElt.qname,
                     attributes=roleRefElt.items())

    # contexts
    for context in sorted(modelXbrl.contexts.values(), key=lambda c: c.objectIndex): # contexts may come from multiple IXDS files
        ignore = targetInstance.createContext(context.entityIdentifier[0],
                                              context.entityIdentifier[1],
                                              'instant' if context.isInstantPeriod else
                                              'duration' if context.isStartEndPeriod
                                              else 'forever',
                                              context.startDatetime,
                                              context.endDatetime,
                                              None,
                                              context.qnameDims, [], [],
                                              id=context.id)
    for unit in sorted(modelXbrl.units.values(), key=lambda u: u.objectIndex): # units may come from multiple IXDS files
        measures = unit.measures
        ignore = targetInstance.createUnit(measures[0], measures[1], id=unit.id)

    modelXbrl.modelManager.showStatus(_("Creating and validating facts"))
    newFactForOldObjId = {}
    invalidFacts = []
    duplicateFacts = frozenset()
    if deduplicationType is not None:
        modelXbrl.modelManager.showStatus(_("Deduplicating facts"))
        deduplicatedFacts = frozenset(ValidateDuplicateFacts.getDeduplicatedFacts(modelXbrl, deduplicationType))
        duplicateFacts = frozenset(f for f in modelXbrl.facts if f not in deduplicatedFacts)

    def createFacts(facts, parent):
        for fact in facts:
            if fact in duplicateFacts:
                ValidateDuplicateFacts.logDeduplicatedFact(modelXbrl, fact)
                continue
            if fact.xValid < VALID and skipInvalid:
                if fact.xValid < NONE: # don't report Redacted facts
                    invalidFacts.append(fact)
            elif fact.isItem: # HF does not de-duplicate, which is currently-desired behavior
                modelConcept = fact.concept # isItem ensures concept is not None
                attrs = {"contextRef": fact.contextID}
                if fact.id:
                    attrs["id"] = fact.id
                if fact.isNumeric:
                    if fact.unitID:
                        attrs["unitRef"] = fact.unitID
                    if fact.get("decimals"):
                        attrs["decimals"] = fact.get("decimals")
                    if fact.get("precision"):
                        attrs["precision"] = fact.get("precision")
                if fact.isNil:
                    attrs[XbrlConst.qnXsiNil] = "true"
                    text = None
                elif ( not(modelConcept.baseXsdType == "token" and modelConcept.isEnumeration)
                       and fact.xValid >= VALID ):
                    text = fact.xValue
                # may need a special case for QNames (especially if prefixes defined below root)
                else:
                    text = fact.rawValue if fact.textValue == INVALIDixVALUE else fact.textValue
                for attrName, attrValue in fact.items():
                    if attrName.startswith("{"):
                        attrs[qname(attrName,fact.nsmap)] = attrValue # using qname allows setting prefix in extracted instance
                newFact = targetInstance.createFact(fact.qname, attributes=attrs, text=text, parent=parent)
                # if fact.isFraction, create numerator and denominator
                newFactForOldObjId[fact.objectIndex] = newFact
                if filingFiles is not None and fact.concept is not None and fact.concept.isTextBlock:
                    # check for img and other filing references so that referenced files are included in the zip.
                    for xmltext in [text] + CDATApattern.findall(text):
                        try:
                            for elt in XML("<body>\n{0}\n</body>\n".format(xmltext)).iter():
                                addLocallyReferencedFile(elt, filingFiles)
                        except (XMLSyntaxError, UnicodeDecodeError):
                            pass  # TODO: Why ignore UnicodeDecodeError?
            elif fact.isTuple:
                attrs = {}
                if fact.id:
                    attrs["id"] = fact.id
                if fact.isNil:
                    attrs[XbrlConst.qnXsiNil] = "true"
                for attrName, attrValue in fact.items():
                    if attrName.startswith("{"):
                        attrs[qname(attrName,fact.nsmap)] = attrValue
                newTuple = targetInstance.createFact(fact.qname, attributes=attrs, parent=parent)
                newFactForOldObjId[fact.objectIndex] = newTuple
                createFacts(fact.modelTupleFacts, newTuple)

    createFacts(modelXbrl.facts, None)
    if invalidFacts:
        modelXbrl.warning("arelle.invalidFactsSkipped",
                          _("Skipping %(count)s invalid facts in saving extracted instance document."),
                          modelObject=invalidFacts, count=len(invalidFacts))
        del invalidFacts[:] # dereference
    modelXbrl.modelManager.showStatus(_("Creating and validating footnotes and relationships"))
    HREF = "{http://www.w3.org/1999/xlink}href"
    footnoteLinks = defaultdict(list)
    footnoteIdCount = {}
    for linkKey, linkPrototypes in modelXbrl.baseSets.items():
        arcrole, linkrole, linkqname, arcqname = linkKey
        if (linkrole and linkqname and arcqname and  # fully specified roles
                arcrole != "XBRL-footnotes" and
                any(lP.modelDocument.type == Type.INLINEXBRL for lP in linkPrototypes)):
            for linkPrototype in linkPrototypes:
                if linkPrototype not in footnoteLinks[linkrole]:
                    footnoteLinks[linkrole].append(linkPrototype)
    for linkrole in sorted(footnoteLinks.keys()):
        for linkPrototype in footnoteLinks[linkrole]:
            newLink = addChild(targetInstance.modelDocument.xmlRootElement,
                               linkPrototype.qname,
                               attributes=linkPrototype.attributes)
            for linkChild in linkPrototype:
                attributes = linkChild.attributes
                if isinstance(linkChild, LocPrototype):
                    if HREF not in linkChild.attributes:
                        linkChild.attributes[HREF] = \
                            "#" + elementFragmentIdentifier(newFactForOldObjId[linkChild.dereference().objectIndex])
                    addChild(newLink, linkChild.qname,
                             attributes=attributes)
                elif isinstance(linkChild, ArcPrototype):
                    addChild(newLink, linkChild.qname, attributes=attributes)
                elif isinstance(linkChild, ModelInlineFootnote):
                    idUseCount = footnoteIdCount.get(linkChild.footnoteID, 0) + 1
                    if idUseCount > 1: # if footnote with id in other links bump the id number
                        attributes = linkChild.attributes.copy()
                        attributes["id"] = "{}_{}".format(attributes["id"], idUseCount)
                    footnoteIdCount[linkChild.footnoteID] = idUseCount
                    newChild = addChild(newLink, linkChild.qname,
                                        attributes=attributes)
                    xmlLang = linkChild.xmlLang
                    if xmlLang is not None and xmlLang != defaultXmlLang: # default
                        newChild.set("{http://www.w3.org/XML/1998/namespace}lang", xmlLang)
                    copyIxFootnoteHtml(linkChild, newChild, targetModelDocument=targetInstance.modelDocument, withText=True)

                    if filingFiles and linkChild.textValue:
                        footnoteHtml = XML("<body/>")
                        copyIxFootnoteHtml(linkChild, footnoteHtml)
                        for elt in footnoteHtml.iter():
                            addLocallyReferencedFile(elt,filingFiles)
    return targetInstance


def _saveTargetDocument(
        modelXbrl,
        targetDocumentFilename,
        targetDocumentSchemaRefs,
        outputZip=None,
        filingFiles=None,
        xbrliNamespacePrefix=None,
        deduplicationType: DeduplicationType | None = None,
        *args, **kwargs):
    targetUrl = modelXbrl.modelManager.cntlr.webCache.normalizeUrl(targetDocumentFilename, modelXbrl.modelDocument.filepath)
    targetUrlParts = targetUrl.rpartition(".")
    targetUrl = targetUrlParts[0] + "_extracted." + targetUrlParts[2]
    modelXbrl.modelManager.showStatus(_("Extracting instance ") + os.path.basename(targetUrl))
    htmlRootElt = modelXbrl.modelDocument.xmlRootElement
    # take baseXmlLang from <html> or <base>
    baseXmlLang = htmlRootElt.get("{http://www.w3.org/XML/1998/namespace}lang") or htmlRootElt.get("lang")
    for ixElt in modelXbrl.modelDocument.xmlRootElement.iterdescendants(tag="{http://www.w3.org/1999/xhtml}body"):
        baseXmlLang = ixElt.get("{http://www.w3.org/XML/1998/namespace}lang") or htmlRootElt.get("lang") or baseXmlLang
    targetInstance = createTargetInstance(
        modelXbrl, targetUrl, targetDocumentSchemaRefs, filingFiles, baseXmlLang,
        xbrliNamespacePrefix=xbrliNamespacePrefix, deduplicationType=deduplicationType,
    )
    targetInstance.saveInstance(overrideFilepath=targetUrl, outputZip=outputZip, xmlcharrefreplace=kwargs.get("encodeSavedXmlChars", False))
    if getattr(modelXbrl, "isTestcaseVariation", False):
        modelXbrl.extractedInlineInstance = True # for validation comparison
    modelXbrl.modelManager.showStatus(_("Saved extracted instance"), 5000)


def _saveTargetInstanceOverriden(deduplicationType: DeduplicationType | None) -> bool:
    """
    Checks if another plugin implements instance extraction, and throws an exception
    if the provided arguments are not compatible.
    :param deduplicationType: The deduplication type to be used, if set.
    :return: True if instance extraction is overridden by another plugin.
    """
    for pluginXbrlMethod in pluginClassMethods('InlineDocumentSet.SavesTargetInstance'):
        if pluginXbrlMethod():
            if deduplicationType is not None:
                raise RuntimeError(_('Deduplication is enabled but could not be performed because instance '
                                     'extraction was performed by another plugin.'))
            return True
    return False


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


def extractTargetDocumentFromIxds(cntlr, options: RuntimeOptions):
    deduplicationTypeArg = getattr(options, "deduplicateIxbrlFacts", None)
    deduplicationType = None if deduplicationTypeArg is None else DeduplicationType(deduplicationTypeArg)
    # skip if another class handles saving (e.g., EdgarRenderer)
    if _saveTargetInstanceOverriden(deduplicationType):
        return
    # extend XBRL-loaded run processing for this option
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


def discoverInlineDocset(entrypointFiles): # [{"file":"url1"}, ...]
    if len(entrypointFiles): # return [{"ixds":[{"file":"url1"}, ...]}]
        # replace contents of entrypointFiles (array object), don't return a new object
        _entrypointFiles = entrypointFiles.copy()
        del entrypointFiles[:]
        entrypointFiles.append( {"ixds": _entrypointFiles} )


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


def isActive():
    return True  # TODO


def loadDTS(modelXbrl, modelIxdsDocument):
    for htmlElt in modelXbrl.ixdsHtmlElements:
        for ixRefElt in htmlElt.iterdescendants(tag=htmlElt.modelDocument.ixNStag + "references"):
            if ixRefElt.get("target") == modelXbrl.ixdsTarget:
                modelIxdsDocument.schemaLinkbaseRefsDiscover(ixRefElt)
                xmlValidate(modelXbrl, ixRefElt) # validate instance elements


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


def saveTargetDocument(
        cntlr,
        runInBackground=False,
        saveTargetFiling=False,
        encodeSavedXmlChars=False,
        xbrliNamespacePrefix=None,
        deduplicationType: DeduplicationType | None = None):
    # skip if another class handles saving (e.g., EdgarRenderer)
    if _saveTargetInstanceOverriden(deduplicationType):
        return
    # save DTS menu item has been invoked
    if (cntlr.modelManager is None or
            cntlr.modelManager.modelXbrl is None or
            cntlr.modelManager.modelXbrl.modelDocument.type not in (Type.INLINEXBRL, Type.INLINEXBRLDOCUMENTSET)):
        cntlr.addToLog("No inline XBRL document set loaded.")
        return
    modelDocument = cntlr.modelManager.modelXbrl.modelDocument
    if modelDocument.type == Type.INLINEXBRLDOCUMENTSET:
        targetFilename = modelDocument.targetDocumentPreferredFilename
        targetSchemaRefs = modelDocument.targetDocumentSchemaRefs
        if targetFilename is None:
            cntlr.addToLog("No inline XBRL document in the inline XBRL document set.")
            return
    else:
        filepath, fileext = os.path.splitext(modelDocument.filepath)
        if fileext not in (".xml", ".xbrl"):
            fileext = ".xbrl"
        targetFilename = filepath + fileext
        targetSchemaRefs = set(modelDocument.relativeUri(referencedDoc.uri)
                               for referencedDoc in modelDocument.referencesDocument.keys()
                               if referencedDoc.type == Type.SCHEMA)
    if runInBackground:
        import threading
        thread = threading.Thread(target=lambda _x = modelDocument.modelXbrl, _f = targetFilename, _s = targetSchemaRefs:
        _saveTargetDocument(_x, _f, _s, deduplicationType=deduplicationType))
        thread.daemon = True
        thread.start()
    else:
        if saveTargetFiling:
            filingZip = zipfile.ZipFile(os.path.splitext(targetFilename)[0] + ".zip", 'w', zipfile.ZIP_DEFLATED, True)
            filingFiles = set()
            # copy referencedDocs to two levels
            def addRefDocs(doc):
                for refDoc in doc.referencesDocument.keys():
                    if refDoc.uri not in filingFiles:
                        filingFiles.add(refDoc.uri)
                        addRefDocs(refDoc)
            addRefDocs(modelDocument)
        else:
            filingZip = None
            filingFiles = None
        _saveTargetDocument(modelDocument.modelXbrl, targetFilename, targetSchemaRefs, filingZip, filingFiles,
                           encodeSavedXmlChars=encodeSavedXmlChars, xbrliNamespacePrefix=xbrliNamespacePrefix,
                           deduplicationType=deduplicationType)
        if saveTargetFiling:
            instDir = os.path.dirname(modelDocument.uri.split(IXDS_DOC_SEPARATOR)[0])
            for refFile in filingFiles:
                if refFile.startswith(instDir):
                    filingZip.write(refFile, modelDocument.relativeUri(refFile))


def skipExpectedInstanceComparison():
    global _skipExpectedInstanceComparison
    return bool(_skipExpectedInstanceComparison)
