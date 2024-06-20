"""
See COPYRIGHT.md for copyright information.
"""
import os
from collections import defaultdict

from arelle import ModelDocument, ModelXbrl, XbrlConst, FunctionIxt, XmlUtil, FileSource
from arelle.DocumentType import DocumentType
from arelle.ModelDocumentReference import ModelDocumentReference
from arelle.ModelObject import ModelObject
from arelle.PluginManager import pluginClassMethods
from arelle.PrototypeDtsObject import LocPrototype, LinkPrototype, ArcPrototype, PrototypeElementTree
from arelle.PythonUtil import normalizeSpace
from arelle.UrlUtil import isHttpUrl
from arelle.XhtmlValidate import ixMsgCode
from arelle.XmlValidate import validate as xmlValidate
from arelle.XmlValidateConst import VALID
from arelle.inline.InlineConstants import DEFAULT_TARGET, IXDS_SURROGATE, IXDS_DOC_SEPARATOR


def discoverInlineDocset(entrypointFiles): # [{"file":"url1"}, ...]
    if len(entrypointFiles): # return [{"ixds":[{"file":"url1"}, ...]}]
        # replace contents of entrypointFiles (array object), don't return a new object
        _entrypointFiles = entrypointFiles.copy()
        del entrypointFiles[:]
        entrypointFiles.append( {"ixds": _entrypointFiles} )


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
                if DocumentType.identify(filesource, filesource.url) in (DocumentType.INSTANCE, DocumentType.INLINEXBRL):
                    reportFiles.append(f)
            else:
                ixdsDir, _sep, ixdsFile = f.rpartition("/")
                if ixdsFile:
                    filesource.select(f)
                    if DocumentType.identify(filesource, filesource.url) == DocumentType.INLINEXBRL:
                        ixdsDirFiles[ixdsDir].append(f)
    if lookOutsideReportsDirectory:
        for f in filesource.dir:
            filesource.select(f)
            if DocumentType.identify(filesource, filesource.url) in (DocumentType.INSTANCE, DocumentType.INLINEXBRL):
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
        if DocumentType.identify(filesource, filesource.url) in (DocumentType.INSTANCE, DocumentType.INLINEXBRL):
            # return the first inline doc
            return f
    return None


def prepareInlineEntrypointFiles(cntlr, entrypointFiles):
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
                                identifiedType = DocumentType.identify(filesource, filesource.url)
                                if identifiedType in (DocumentType.INSTANCE, DocumentType.INLINEXBRL):
                                    urlsByType.setdefault(identifiedType, []).append(filesource.url)
                        filesource.close()
                    elif os.path.isdir(_files[0]):
                        _fileDir = _files[0]
                        for _localName in os.listdir(_fileDir):
                            _file = os.path.join(_fileDir, _localName)
                            if os.path.isfile(_file):
                                filesource = FileSource.openFileSource(_file, cntlr)
                                identifiedType = DocumentType.identify(filesource, filesource.url)
                                if identifiedType in (DocumentType.INSTANCE, DocumentType.INLINEXBRL):
                                    urlsByType.setdefault(identifiedType, []).append(filesource.url)
                                filesource.close()
                    if urlsByType:
                        _files = []
                        # use inline instances, if any, else non-inline instances
                        for identifiedType in (DocumentType.INLINEXBRL, DocumentType.INSTANCE):
                            for url in urlsByType.get(identifiedType, []):
                                _files.append(url)
                            if _files:
                                break # found inline (or non-inline) entrypoint files, don't look for any other type
                if len(_files) > 0:
                    docsetSurrogatePath = os.path.join(os.path.dirname(_files[0]), IXDS_SURROGATE)
                    entrypointFile["file"] = docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(_files)


def _ixdsTargets(ixdsHtmlElements):
    return sorted(set(elt.get("target", DEFAULT_TARGET)
                      for htmlElt in ixdsHtmlElements
                      for elt in htmlElt.iterfind(f".//{{{htmlElt.modelDocument.ixNS}}}references")))


def discoverInlineXbrlDocumentSet(modelDocument, *args, **kwargs):
    from arelle.inline.ixds.IxdsModelDocument import IxdsModelDocument
    if isinstance(modelDocument, IxdsModelDocument):
        return modelDocument.discoverInlineXbrlDocumentSet()
    return False  # not discoverable by this plug-in


def identifyInlineXbrlDocumentSet(modelXbrl, rootNode, filepath):
    from arelle.inline.ixds.IxdsModelDocument import IxdsModelDocument
    for manifestElt in rootNode.iter(tag="{http://disclosure.edinet-fsa.go.jp/2013/manifest}manifest"):
        # it's an edinet fsa manifest of an inline XBRL document set
        return (DocumentType.INLINEXBRLDOCUMENTSET, IxdsModelDocument, manifestElt)
    return None # not a document set


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
        ixdocset = ModelDocument.create(modelXbrl, DocumentType.INLINEXBRLDOCUMENTSET, docsetUrl, isEntry=True, initialXml="".join(xml))
        ixdocset.type = DocumentType.INLINEXBRLDOCUMENTSET
        ixdocset.targetDocumentPreferredFilename = None # possibly no inline docs in this doc set
        for i, elt in enumerate(ixdocset.xmlRootElement.iter(tag="instance")):
            # load ix document
            if ixdocs:
                ixdoc = ixdocs[i]
            else:
                ixdoc = ModelDocument.load(modelXbrl, elt.text, referringElement=elt, isDiscovered=True)
            if ixdoc is not None:
                if ixdoc.type == DocumentType.INLINEXBRL:
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
            ixdsDiscover(modelXbrl, ixdocset, bool(ixdocs)) # compile cross-document IXDS references
            return ixdocset
    return None


# inline document set level compilation
# modelIxdsDocument is an inlineDocumentSet or entry inline document (if not a document set)
#   note that multi-target and multi-instance facts may have html elements belonging to primary ixds instead of this instance ixds
def ixdsDiscover(modelXbrl, modelIxdsDocument, setTargetModelXbrl=False):
    selectTargetDocument(modelXbrl, modelIxdsDocument)
    for selector in pluginClassMethods("ModelDocument.SelectIxdsTarget"):
        selector(modelXbrl, modelIxdsDocument)
    # extract for a single target document
    ixdsTarget = getattr(modelXbrl, "ixdsTarget", None)
    # compile inline result set
    ixdsEltById = modelXbrl.ixdsEltById = defaultdict(list)
    for htmlElement in modelXbrl.ixdsHtmlElements:
        for elt in htmlElement.iterfind(".//*[@id]"):
            if isinstance(elt,ModelObject) and elt.id:
                ixdsEltById[elt.id].append(elt)

    # TODO: ixdsEltById duplication should be tested here and removed from ValidateXbrlDTS (about line 346 after if name == "id" and attrValue in val.elementIDs)
    footnoteRefs = defaultdict(list)
    tupleElements = []
    continuationElements = {}
    continuationReferences = defaultdict(set) # set of elements that have continuedAt source value
    tuplesByTupleID = {}
    factsByFactID = {} # non-tuple facts
    factTargetIDs = set() # target IDs referenced on facts
    factTargetContextRefs = defaultdict(set) # index is target, value is set of contextRefs
    factTargetUnitRefs = defaultdict(set) # index is target, value is set of unitRefs
    targetRoleUris = defaultdict(set) # index is target, value is set of roleUris
    targetArcroleUris = defaultdict(set) # index is target, value is set of arcroleUris
    targetReferenceAttrElts = defaultdict(dict) # target dict by attrname of elts
    targetReferenceAttrVals = defaultdict(dict) # target dict by attrname of attr value
    targetReferencePrefixNs = defaultdict(dict) # target dict by prefix, namespace
    targetReferencesIDs = {} # target dict by id of reference elts
    modelInlineFootnotesById = {} # inline 1.1 ixRelationships and ixFootnotes
    modelXbrl.targetRoleRefs = {} # roleRefs used by selected target
    modelXbrl.targetArcroleRefs = {}  # arcroleRefs used by selected target
    modelXbrl.targetRelationships = set() # relationship elements used by selected target
    targetModelXbrl = modelXbrl if setTargetModelXbrl else None # modelXbrl of target for contexts/units in multi-target/multi-instance situation
    assignUnusedContextsUnits = (not setTargetModelXbrl and not ixdsTarget and
                                 not getattr(modelXbrl, "supplementalModelXbrls", ()) and (
                                         not getattr(modelXbrl, "targetIXDSesToLoad", ()) or
                                         set(e.modelDocument for e in modelXbrl.ixdsHtmlElements) ==
                                         set(x.modelDocument for e in getattr(modelXbrl, "targetIXDSesToLoad", ()) for x in e[1])))
    hasResources = hasHeader = False
    for htmlElement in modelXbrl.ixdsHtmlElements:
        mdlDoc = htmlElement.modelDocument
        ixNStag = mdlDoc.ixNStag
        for modelInlineTuple in htmlElement.iterdescendants(tag=ixNStag + "tuple"):
            if isinstance(modelInlineTuple,ModelObject):
                modelInlineTuple.unorderedTupleFacts = defaultdict(list)
                if modelInlineTuple.qname is not None:
                    if modelInlineTuple.tupleID:
                        if modelInlineTuple.tupleID not in tuplesByTupleID:
                            tuplesByTupleID[modelInlineTuple.tupleID] = modelInlineTuple
                        else:
                            modelXbrl.error(ixMsgCode("tupleIdDuplication", modelInlineTuple, sect="validation"),
                                            _("Inline XBRL tuples have same tupleID %(tupleID)s: %(qname1)s and %(qname2)s"),
                                            modelObject=(modelInlineTuple,tuplesByTupleID[modelInlineTuple.tupleID]),
                                            tupleID=modelInlineTuple.tupleID, qname1=modelInlineTuple.qname,
                                            qname2=tuplesByTupleID[modelInlineTuple.tupleID].qname)
                    tupleElements.append(modelInlineTuple)
                    for r in modelInlineTuple.footnoteRefs:
                        footnoteRefs[r].append(modelInlineTuple)
                    if modelInlineTuple.id:
                        factsByFactID[modelInlineTuple.id] = modelInlineTuple
                factTargetIDs.add(modelInlineTuple.get("target"))
        for modelInlineFact in htmlElement.iterdescendants(ixNStag + "nonNumeric", ixNStag + "nonFraction", ixNStag + "fraction"):
            if isinstance(modelInlineFact,ModelObject):
                _target = modelInlineFact.get("target")
                factTargetContextRefs[_target].add(modelInlineFact.get("contextRef"))
                factTargetUnitRefs[_target].add(modelInlineFact.get("unitRef"))
                if modelInlineFact.id:
                    factsByFactID[modelInlineFact.id] = modelInlineFact
        for elt in htmlElement.iterdescendants(tag=ixNStag + "continuation"):
            if isinstance(elt,ModelObject) and elt.id:
                continuationElements[elt.id] = elt
        for elt in htmlElement.iterdescendants(tag=XbrlConst.qnIXbrl11Footnote.clarkNotation):
            if isinstance(elt,ModelObject):
                modelInlineFootnotesById[elt.footnoteID] = elt
        for elt in htmlElement.iterdescendants(tag=ixNStag + "references"):
            if isinstance(elt,ModelObject):
                target = elt.get("target")
                targetReferenceAttrsDict = targetReferenceAttrElts[target]
                for attrName, attrValue in elt.items():
                    if attrName.startswith('{') and not attrName.startswith(ixNStag) and attrName != "{http://www.w3.org/XML/1998/namespace}base":
                        if attrName in targetReferenceAttrsDict:
                            modelXbrl.error(ixMsgCode("referencesAttributeDuplication",ns=mdlDoc.ixNS,name="references",sect="validation"),
                                            _("Inline XBRL ix:references attribute %(name)s duplicated in target %(target)s"),
                                            modelObject=(elt, targetReferenceAttrsDict[attrName]), name=attrName, target=target)
                        else:
                            targetReferenceAttrsDict[attrName] = elt
                            targetReferenceAttrVals[target][attrName] = attrValue # use qname to preserve prefix
                    if attrName.startswith("{http://www.xbrl.org/2003/instance}"):
                        modelXbrl.error(ixMsgCode("qualifiedAttributeDisallowed",ns=mdlDoc.ixNS,name="references",sect="constraint"),
                                        _("Inline XBRL element %(element)s has disallowed attribute %(name)s"),
                                        modelObject=elt, element=str(elt.elementQname), name=attrName)
                if elt.id:
                    if ixdsEltById[elt.id] != [elt]:
                        modelXbrl.error(ixMsgCode("referencesIdDuplication",ns=mdlDoc.ixNS,name="references",sect="validation"),
                                        _("Inline XBRL ix:references id %(id)s duplicated in inline document set"),
                                        modelObject=ixdsEltById[elt.id], id=elt.id)
                    if target in targetReferencesIDs:
                        modelXbrl.error(ixMsgCode("referencesTargetId",ns=mdlDoc.ixNS,name="references",sect="validation"),
                                        _("Inline XBRL has multiple ix:references with id in target %(target)s"),
                                        modelObject=(elt, targetReferencesIDs[target]), target=target)
                    else:
                        targetReferencesIDs[target] = elt
                targetReferencePrefixNsDict = targetReferencePrefixNs[target]
                for _prefix, _ns in elt.nsmap.items():
                    if _prefix in targetReferencePrefixNsDict and _ns != targetReferencePrefixNsDict[_prefix][0]:
                        modelXbrl.error(ixMsgCode("referencesNamespacePrefixConflict",ns=mdlDoc.ixNS,name="references",sect="validation"),
                                        _("Inline XBRL ix:references prefix %(prefix)s has multiple namespaces %(ns1)s and %(ns2)s in target %(target)s"),
                                        modelObject=(elt, targetReferencePrefixNsDict[_prefix][1]), prefix=_prefix, ns1=_ns, ns2=targetReferencePrefixNsDict[_prefix], target=target)
                    else:
                        targetReferencePrefixNsDict[_prefix] = (_ns, elt)

        for hdrElt in htmlElement.iterdescendants(tag=ixNStag + "header"):
            hasHeader = True
            for elt in hdrElt.iterchildren(tag=ixNStag + "resources"):
                hasResources = True
                for subEltTag in ("{http://www.xbrl.org/2003/instance}context","{http://www.xbrl.org/2003/instance}unit"):
                    for resElt in elt.iterdescendants(tag=subEltTag):
                        if resElt.id:
                            if ixdsEltById[resElt.id] != [resElt]:
                                modelXbrl.error(ixMsgCode("resourceIdDuplication",ns=mdlDoc.ixNS,name="resources",sect="validation"),
                                                _("Inline XBRL ix:resources descendant id %(id)s duplicated in inline document set"),
                                                modelObject=ixdsEltById[resElt.id], id=resElt.id)
    if not hasHeader:
        modelXbrl.error(ixMsgCode("missingHeader", ns=mdlDoc.ixNS, name="header", sect="validation"),
                        _("Inline XBRL ix:header element not found"),
                        modelObject=modelXbrl)
    if not hasResources:
        modelXbrl.error(ixMsgCode("missingResources", ns=mdlDoc.ixNS, name="resources", sect="validation"),
                        _("Inline XBRL ix:resources element not found"),
                        modelObject=modelXbrl)

    del ixdsEltById, targetReferencesIDs

    # discovery of relationships which are used by target documents
    for htmlElement in modelXbrl.ixdsHtmlElements:
        for modelInlineRel in htmlElement.iterdescendants(tag=XbrlConst.qnIXbrl11Relationship.clarkNotation):
            if isinstance(modelInlineRel,ModelObject):
                linkrole = modelInlineRel.get("linkRole", XbrlConst.defaultLinkRole)
                arcrole = modelInlineRel.get("arcrole", XbrlConst.factFootnote)
                sourceFactTargets = set()
                for id in modelInlineRel.get("fromRefs","").split():
                    if id in factsByFactID:
                        _target = factsByFactID[id].get("target")
                        targetRoleUris[_target].add(linkrole)
                        targetArcroleUris[_target].add(arcrole)
                        sourceFactTargets.add(_target)
                for id in modelInlineRel.get("toRefs","").split():
                    if id in factsByFactID:
                        _target = factsByFactID[id].get("target")
                        targetRoleUris[_target].add(linkrole)
                        targetArcroleUris[_target].add(arcrole)
                    elif id in modelInlineFootnotesById:
                        footnoteRole = modelInlineFootnotesById[id].get("footnoteRole")
                        if footnoteRole:
                            for _target in sourceFactTargets:
                                targetRoleUris[_target].add(footnoteRole)

    contextRefs = factTargetContextRefs[ixdsTarget]
    unitRefs = factTargetUnitRefs[ixdsTarget]
    allContextRefs = set.union(*factTargetContextRefs.values())
    allUnitRefs = set.union(*factTargetUnitRefs.values())

    # discovery of contexts, units and roles which are used by target document
    for htmlElement in modelXbrl.ixdsHtmlElements:
        mdlDoc = htmlElement.modelDocument
        ixNStag = mdlDoc.ixNStag

        for inlineElement in htmlElement.iterdescendants(tag=ixNStag + "resources"):
            for elt in inlineElement.iterchildren("{http://www.xbrl.org/2003/instance}context"):
                id = elt.get("id")
                if id in contextRefs or (assignUnusedContextsUnits and id not in allContextRefs):
                    modelIxdsDocument.contextDiscover(elt, setTargetModelXbrl)
            for elt in inlineElement.iterchildren("{http://www.xbrl.org/2003/instance}unit"):
                id = elt.get("id")
                if id in unitRefs or (assignUnusedContextsUnits and id not in allUnitRefs):
                    modelIxdsDocument.unitDiscover(elt, setTargetModelXbrl)
            for refElement in inlineElement.iterchildren("{http://www.xbrl.org/2003/linkbase}roleRef"):
                r = refElement.get("roleURI")
                if r in targetRoleUris[ixdsTarget]:
                    modelXbrl.targetRoleRefs[r] = refElement
                    if modelIxdsDocument.discoverHref(refElement) is None: # discover role-defining schema file
                        modelXbrl.error("xmlSchema:requiredAttribute",
                                        _("Reference for roleURI href attribute missing or malformed"),
                                        modelObject=refElement)
            for refElement in inlineElement.iterchildren("{http://www.xbrl.org/2003/linkbase}arcroleRef"):
                r = refElement.get("arcroleURI")
                if r in targetArcroleUris[ixdsTarget]:
                    modelXbrl.targetArcroleRefs[r] = refElement
                    if modelIxdsDocument.discoverHref(refElement) is None: # discover arcrole-defining schema file
                        modelXbrl.error("xmlSchema:requiredAttribute",
                                        _("Reference for arcroleURI href attribute missing or malformed"),
                                        modelObject=refElement)


    del factTargetContextRefs, factTargetUnitRefs

    # root elements by target
    modelXbrl.ixTargetRootElements = {}
    for target in targetReferenceAttrElts.keys() | {None}: # need default target in case any facts have no or invalid target
        try:
            modelXbrl.ixTargetRootElements[target] = elt = modelIxdsDocument.parser.makeelement(
                XbrlConst.qnPrototypeXbrliXbrl.clarkNotation, attrib=targetReferenceAttrVals.get(target),
                nsmap=dict((p,n) for p,(n,e) in targetReferencePrefixNs.get(target,{}).items()))
            elt.init(modelIxdsDocument)
        except Exception as err:
            modelXbrl.error(type(err).__name__,
                            _("Unrecoverable error creating target instance: %(error)s"),
                            modelObject=modelXbrl, error=err)

    def locateFactInTuple(modelFact, tuplesByTupleID, ixNStag):
        tupleRef = modelFact.tupleRef
        tuple = None
        if tupleRef:
            if tupleRef not in tuplesByTupleID:
                modelXbrl.error(ixMsgCode("tupleRefMissing", modelFact, sect="validation"),
                                _("Inline XBRL tupleRef %(tupleRef)s not found"),
                                modelObject=modelFact, tupleRef=tupleRef)
            else:
                tuple = tuplesByTupleID[tupleRef]
        else:
            for tupleParent in modelFact.iterancestors(tag=ixNStag + '*'):
                if tupleParent.localName == "tuple":
                    tuple = tupleParent
                break
        if tuple is not None:
            if modelFact.order is not None: # None when order missing failed validation
                tuple.unorderedTupleFacts[modelFact.order].append(modelFact)
            else:
                modelXbrl.error(ixMsgCode("tupleMemberOrderMissing", modelFact, sect="validation"),
                                _("Inline XBRL tuple member %(qname)s must have a numeric order attribute"),
                                modelObject=modelFact, qname=modelFact.qname)
            if modelFact.get("target") == tuple.get("target"):
                modelFact._ixFactParent = tuple # support ModelInlineFact parentElement()
            else:
                modelXbrl.error(ixMsgCode("tupleMemberDifferentTarget", modelFact, sect="validation"),
                                _("Inline XBRL tuple member %(qname)s must have a tuple parent %(tuple)s with same target"),
                                modelObject=modelFact, qname=modelFact.qname, tuple=tuple.qname)
        else:
            if modelFact.get("target") == ixdsTarget: # only process facts with target match
                modelXbrl.modelXbrl.facts.append(modelFact)
            try:
                modelFact._ixFactParent = modelXbrl.ixTargetRootElements[modelFact.get("target")]
            except KeyError:
                modelFact._ixFactParent = modelXbrl.ixTargetRootElements[None]

    def locateContinuation(element):
        contAt = element.get("continuedAt")
        if contAt: # has continuation
            chain = [element] # implement non-recursively for very long continuaion chains
            while contAt:
                continuationReferences[contAt].add(element)
                if contAt not in continuationElements:
                    if contAt in element.modelDocument.idObjects:
                        _contAtTarget = element.modelDocument.idObjects[contAt]
                        modelXbrl.error(ixMsgCode("continuationTarget", element, sect="validation"),
                                        _("continuedAt %(continuationAt)s target is an %(targetElement)s element instead of ix:continuation element."),
                                        modelObject=(element, _contAtTarget), continuationAt=contAt, targetElement=_contAtTarget.elementQname)
                    else:
                        modelXbrl.error(ixMsgCode("continuationMissing", element, sect="validation"),
                                        _("Inline XBRL continuation %(continuationAt)s not found"),
                                        modelObject=element, continuationAt=contAt)
                    break
                else:
                    contElt = continuationElements[contAt]
                    if contElt in chain:
                        cycle = ", ".join(e.get("continuedAt") for e in chain)
                        chain.append(contElt) # makes the cycle clear
                        modelXbrl.error(ixMsgCode("continuationCycle", element, sect="validation"),
                                        _("Inline XBRL continuation cycle: %(continuationCycle)s"),
                                        modelObject=chain, continuationCycle=cycle)
                        break
                    else:
                        chain.append(contElt)
                        element._continuationElement = contElt
                        element = contElt # loop to continuation element
                        contAt = element.get("continuedAt")
            # check if any chain element is descendant of another
            chainSet = set(chain)
            for chainElt in chain:
                for chainEltAncestor in chainElt.iterancestors(tag=chainElt.modelDocument.ixNStag + '*'):
                    if chainEltAncestor in chainSet:
                        if hasattr(chain[0], "_continuationElement"):
                            del chain[0]._continuationElement # break chain to prevent looping in chain
                        modelXbrl.error(ixMsgCode("continuationChainNested", chainElt, sect="validation"),
                                        _("Inline XBRL continuation chain element %(ancestorElement)s has descendant element %(descendantElement)s"),
                                        modelObject=(chainElt,chainEltAncestor),
                                        ancestorElement=chainEltAncestor.id or chainEltAncestor.get("name",chainEltAncestor.get("continuedAt")),
                                        descendantElement=chainElt.id or chainElt.get("name",chainElt.get("continuedAt")))

    def checkTupleIxDescendants(tupleFact, parentElt):
        for childElt in parentElt.iterchildren():
            if isinstance(childElt,ModelObject) and childElt.namespaceURI in XbrlConst.ixbrlAll:
                if childElt.localName in ("numerator", "denominator"):
                    modelXbrl.error(ixMsgCode("tupleContentError", tupleFact, sect="validation"),
                                    _("Inline XBRL tuple content illegal %(qname)s"),
                                    modelObject=(tupleFact, childElt), qname=childElt.qname)
            else:
                checkTupleIxDescendants(tupleFact, childElt)

    def addItemFactToTarget(modelInlineFact):
        if setTargetModelXbrl:
            modelInlineFact.targetModelXbrl = modelXbrl # fact's owning IXDS overrides initial loading document IXDS
        if modelInlineFact.concept is None:
            modelXbrl.error(ixMsgCode("missingReferences", modelInlineFact, name="references", sect="validation"),
                            _("Instance fact missing schema definition: %(qname)s of Inline Element %(localName)s"),
                            modelObject=modelInlineFact, qname=modelInlineFact.qname, localName=modelInlineFact.elementQname)
        elif modelInlineFact.isFraction != (modelInlineFact.localName == "fraction"):
            modelXbrl.error(ixMsgCode("fractionDeclaration", modelInlineFact, name="fraction", sect="validation"),
                            _("Inline XBRL element %(qname)s base type %(type)s mapped by %(localName)s"),
                            modelObject=modelInlineFact, qname=modelInlineFact.qname, localName=modelInlineFact.elementQname,
                            type=modelInlineFact.concept.baseXsdType)
        else:
            modelIxdsDocument.modelXbrl.factsInInstance.add( modelInlineFact )

    _customTransforms = modelXbrl.modelManager.customTransforms or {}
    for htmlElement in modelXbrl.ixdsHtmlElements:
        mdlDoc = htmlElement.modelDocument
        ixNStag = mdlDoc.ixNStag
        # hook up tuples to their container
        for tupleFact in tupleElements:
            if tupleFact.modelDocument == mdlDoc:
                locateFactInTuple(tupleFact, tuplesByTupleID, ixNStag)
                if tupleFact.get("target") == ixdsTarget:
                    addItemFactToTarget(tupleFact) # needs to be in factsInInstance


        for modelInlineFact in htmlElement.iterdescendants(ixNStag + "nonNumeric", ixNStag + "nonFraction", ixNStag + "fraction"):
            _target = modelInlineFact.get("target")
            factTargetIDs.add(_target)
            if modelInlineFact.qname is not None: # must have a qname to be in facts
                if _target == ixdsTarget: # if not the selected target, schema isn't loaded
                    addItemFactToTarget(modelInlineFact)
                locateFactInTuple(modelInlineFact, tuplesByTupleID, ixNStag)
                locateContinuation(modelInlineFact)
                for r in modelInlineFact.footnoteRefs:
                    footnoteRefs[r].append(modelInlineFact)
                if modelInlineFact.elementQname.localName == "fraction":
                    childCounts = {}
                    for child in modelInlineFact.iter(ixNStag + "*"):
                        childCounts[child.elementQname.localName] = childCounts.get(child.elementQname.localName, 0) + 1
                        if child.elementQname.localName == "fraction":
                            for attr in modelInlineFact.attrib:
                                if (attr.startswith("{") or attr == "unitRef") and modelInlineFact.get(attr,"").strip() != child.get(attr,"").strip():
                                    modelXbrl.error(ixMsgCode("fractionChildAttributes", modelInlineFact, sect="validation"),
                                                    _("Inline XBRL nested fractions must have same attribute values for %(attr)s"),
                                                    modelObject=(modelInlineFact,child), attr=attr)
                    if modelInlineFact.isNil:
                        if "numerator" in childCounts or "denominator" in childCounts:
                            modelXbrl.error(ixMsgCode("nilFractionChildren", modelInlineFact, sect="constraint"),
                                            _("Inline XBRL nil fractions must not have any ix:numerator or ix:denominator children"),
                                            modelObject=modelInlineFact)
                    else:
                        if childCounts.get("numerator",0) != 1 or childCounts.get("denominator",0) != 1:
                            modelXbrl.error(ixMsgCode("fractionChildren", modelInlineFact, sect="constraint"),
                                            _("Inline XBRL fractions must have one ix:numerator and one ix:denominator child"),
                                            modelObject=modelInlineFact)
                    disallowedChildren = sorted((k for k in childCounts.keys() if k not in ("numerator", "denominator", "fraction") ))
                    if disallowedChildren:
                        modelXbrl.error(ixMsgCode("fractionChildren", modelInlineFact, sect="constraint"),
                                        _("Inline XBRL fraction disallowed children: %(disallowedChildren)s"),
                                        modelObject=modelInlineFact, disallowedChildren=", ".join(disallowedChildren))
                elif modelInlineFact.elementQname.localName == "nonFraction":
                    if not modelInlineFact.isNil:
                        if any(True for e in modelInlineFact.iterchildren("{*}*")) and (
                                modelInlineFact.text is not None or any(e.tail is not None for e in modelInlineFact.iterchildren())):
                            modelXbrl.error(ixMsgCode("nonFractionChildren", modelInlineFact, sect="constraint"),
                                            _("Inline XBRL nonFraction must have only one child nonFraction or text/whitespace but not both"),
                                            modelObject=modelInlineFact)
                fmt = modelInlineFact.format
                if fmt:
                    if fmt in _customTransforms:
                        pass
                    elif fmt.namespaceURI not in FunctionIxt.ixtNamespaceFunctions:
                        modelXbrl.error(ixMsgCode("invalidTransformation", modelInlineFact, sect="validation"),
                                        _("Fact %(fact)s has unrecognized transformation namespace %(namespace)s"),
                                        modelObject=modelInlineFact, fact=modelInlineFact.qname, transform=fmt, namespace=fmt.namespaceURI)
                        modelInlineFact.setInvalid()
                    elif fmt.localName not in FunctionIxt.ixtNamespaceFunctions[fmt.namespaceURI]:
                        modelXbrl.error(ixMsgCode("invalidTransformation", modelInlineFact, sect="validation"),
                                        _("Fact %(fact)s has unrecognized transformation name %(name)s"),
                                        modelObject=modelInlineFact, fact=modelInlineFact.qname, transform=fmt, name=fmt.localName)
                        modelInlineFact.setInvalid()
            else:
                modelXbrl.error(ixMsgCode("missingReferences", modelInlineFact, name="references", sect="validation"),
                                _("Instance fact missing schema definition: %(qname)s of Inline Element %(localName)s"),
                                modelObject=modelInlineFact, qname=modelInlineFact.get("name","(no name)"), localName=modelInlineFact.elementQname)

        # order tuple facts
        for tupleFact in tupleElements:
            # check for duplicates
            for order, facts in tupleFact.unorderedTupleFacts.items():
                if len(facts) > 1:
                    if not all(normalizeSpace(facts[0].value) == normalizeSpace(f.value) and
                               all(normalizeSpace(facts[0].get(attr)) == normalizeSpace(f.get(attr))
                                   for attr in facts[0].keys() if attr != "order")
                               for f in facts[1:]):
                        modelXbrl.error(ixMsgCode("tupleSameOrderMembersUnequal", facts[0], sect="validation"),
                                        _("Inline XBRL tuple members %(qnames)s values %(values)s and attributes not whitespace-normalized equal"),
                                        modelObject=facts, qnames=", ".join(str(f.qname) for f in facts),
                                        values=", ".join(f.value for f in facts))
            # check nearest ix: descendants
            checkTupleIxDescendants(tupleFact, tupleFact)
            tupleFact.modelTupleFacts = [facts[0] # this deduplicates by order number
                                         for order,facts in sorted(tupleFact.unorderedTupleFacts.items(), key=lambda i:i[0])
                                         if len(facts) > 0]

        # check for tuple cycles
        def checkForTupleCycle(parentTuple, tupleNesting):
            for fact in parentTuple.modelTupleFacts:
                if fact in tupleNesting:
                    tupleNesting.append(fact)
                    modelXbrl.error(ixMsgCode("tupleNestingCycle", fact, sect="validation"),
                                    _("Tuple nesting cycle: %(tupleCycle)s"),
                                    modelObject=tupleNesting, tupleCycle="->".join(str(t.qname) for t in tupleNesting))
                    tupleNesting.pop()
                else:
                    tupleNesting.append(fact)
                    checkForTupleCycle(fact, tupleNesting)
                    tupleNesting.pop()

        for tupleFact in tupleElements:
            checkForTupleCycle(tupleFact, [tupleFact])

        for modelInlineFootnote in htmlElement.iterdescendants(tag=XbrlConst.qnIXbrl11Footnote.clarkNotation):
            if isinstance(modelInlineFootnote,ModelObject):
                locateContinuation(modelInlineFootnote)

        for elt in htmlElement.iterdescendants(ixNStag + "exclude"):
            if not any(True for ancestor in elt.iterancestors(ixNStag + "continuation", ixNStag + "footnote", ixNStag + "nonNumeric")):
                modelXbrl.error(ixMsgCode("excludeMisplaced", elt, sect="constraint"),
                                _("Ix:exclude must be a descendant of descendant of at least one ix:continuation, ix:footnote or ix:nonNumeric element."),
                                modelObject=elt)

    # validate particle structure of elements after transformations and established tuple structure
    fractionTermTags = (ixNStag + "numerator", ixNStag + "denominator")
    for rootModelFact in modelXbrl.facts:
        # validate XBRL (after complete document set is loaded)
        if rootModelFact.localName == "fraction":
            numDenom = [None,None]
            for i, tag in enumerate(fractionTermTags):
                for modelInlineFractionTerm in rootModelFact.iterchildren(tag=tag):
                    xmlValidate(modelXbrl, modelInlineFractionTerm, ixFacts=True)
                    if modelInlineFractionTerm.xValid >= VALID:
                        numDenom[i] = modelInlineFractionTerm.xValue
            rootModelFact._fractionValue = numDenom
        xmlValidate(modelXbrl, rootModelFact, ixFacts=True)

    if len(targetReferenceAttrElts) == 0:
        modelXbrl.error(ixMsgCode("missingReferences", None, name="references", sect="validation"),
                        _("There must be at least one reference"),
                        modelObject=modelXbrl)
    _missingReferenceTargets = factTargetIDs - set(targetReferenceAttrElts.keys())
    if _missingReferenceTargets:
        modelXbrl.error(ixMsgCode("missingReferenceTargets", None, name="references", sect="validation"),
                        _("Found no ix:references element%(plural)s having target%(plural)s '%(missingReferenceTargets)s' in IXDS."),
                        modelObject=modelXbrl, plural=("s" if len(_missingReferenceTargets) > 1 else ""),
                        missingReferenceTargets=", ".join(sorted("(default)" if t is None else t
                                                                 for t in _missingReferenceTargets)))

    if ixdsTarget not in factTargetIDs and ixdsTarget not in targetReferenceAttrElts.keys():
        modelXbrl.warning("arelle:ixdsTargetNotDefined",
                          _("Target parameter %(ixdsTarget)s is not a specified IXDS target property"),
                          modelObject=modelXbrl, ixdsTarget=ixdsTarget)

    del targetReferenceAttrElts, targetReferencePrefixNs, targetReferenceAttrVals, factTargetIDs


    footnoteLinkPrototypes = {}
    # inline 1.1 link prototypes, one per link role (so only one extended link element is produced per link role)
    linkPrototypes = {}
    # inline 1.1 ixRelationships and ixFootnotes
    linkModelInlineFootnoteIds = defaultdict(set)
    linkModelLocIds = defaultdict(set)
    for htmlElement in modelXbrl.ixdsHtmlElements:
        mdlDoc = htmlElement.modelDocument
        # inline 1.0 ixFootnotes, build resources (with ixContinuation)
        for modelInlineFootnote in htmlElement.iterdescendants(tag=XbrlConst.qnIXbrlFootnote.clarkNotation):
            if isinstance(modelInlineFootnote,ModelObject):
                # link
                linkrole = modelInlineFootnote.get("footnoteLinkRole", XbrlConst.defaultLinkRole)
                arcrole = modelInlineFootnote.get("arcrole", XbrlConst.factFootnote)
                footnoteID = modelInlineFootnote.footnoteID or ""
                # check if any footnoteRef fact is in this target instance
                if not any(modelFact.get("target") == ixdsTarget for modelFact in footnoteRefs[footnoteID]):
                    continue # skip footnote, it's not in this target document
                footnoteLocLabel = footnoteID + "_loc"
                if linkrole in footnoteLinkPrototypes:
                    linkPrototype = footnoteLinkPrototypes[linkrole]
                else:
                    linkPrototype = LinkPrototype(modelIxdsDocument, mdlDoc.xmlRootElement, XbrlConst.qnLinkFootnoteLink, linkrole)
                    footnoteLinkPrototypes[linkrole] = linkPrototype
                    for baseSetKey in (("XBRL-footnotes",None,None,None),
                                       ("XBRL-footnotes",linkrole,None,None),
                                       (arcrole,linkrole,XbrlConst.qnLinkFootnoteLink, XbrlConst.qnLinkFootnoteArc),
                                       (arcrole,linkrole,None,None),
                                       (arcrole,None,None,None)):
                        modelXbrl.baseSets[baseSetKey].append(linkPrototype)
                # locs
                for modelFact in footnoteRefs[footnoteID]:
                    locPrototype = LocPrototype(modelIxdsDocument, linkPrototype, footnoteLocLabel, modelFact)
                    linkPrototype.childElements.append(locPrototype)
                    linkPrototype.labeledResources[footnoteLocLabel].append(locPrototype)
                # resource
                linkPrototype.childElements.append(modelInlineFootnote)
                linkPrototype.labeledResources[footnoteID].append(modelInlineFootnote)
                # arc
                linkPrototype.childElements.append(ArcPrototype(mdlDoc, linkPrototype, XbrlConst.qnLinkFootnoteArc,
                                                                footnoteLocLabel, footnoteID,
                                                                linkrole, arcrole, sourceElement=modelInlineFootnote))

        for modelInlineRel in htmlElement.iterdescendants(tag=XbrlConst.qnIXbrl11Relationship.clarkNotation):
            if isinstance(modelInlineRel,ModelObject):
                linkrole = modelInlineRel.get("linkRole", XbrlConst.defaultLinkRole)
                if linkrole not in linkPrototypes:
                    linkPrototypes[linkrole] = LinkPrototype(modelIxdsDocument, mdlDoc.xmlRootElement, XbrlConst.qnLinkFootnoteLink, linkrole, sourceElement=modelInlineRel)


    for htmlElement in modelXbrl.ixdsHtmlElements:
        mdlDoc = htmlElement.modelDocument
        for modelInlineRel in htmlElement.iterdescendants(tag=XbrlConst.qnIXbrl11Relationship.clarkNotation):
            if isinstance(modelInlineRel,ModelObject):
                fromLabels = set()
                relHasFromFactsInTarget = relHasToObjectsInTarget = False
                for fromId in modelInlineRel.get("fromRefs","").split():
                    fromLabels.add(fromId)
                    if not relHasFromFactsInTarget and fromId in factsByFactID and factsByFactID[fromId].get("target") == ixdsTarget:
                        relHasFromFactsInTarget = True
                linkrole = modelInlineRel.get("linkRole", XbrlConst.defaultLinkRole)
                arcrole = modelInlineRel.get("arcrole", XbrlConst.factFootnote)
                linkPrototype = linkPrototypes[linkrole]
                for baseSetKey in (("XBRL-footnotes",None,None,None),
                                   ("XBRL-footnotes",linkrole,None,None),
                                   (arcrole,linkrole,XbrlConst.qnLinkFootnoteLink, XbrlConst.qnLinkFootnoteArc),
                                   (arcrole,linkrole,None,None),
                                   (arcrole,None,None,None)):
                    if linkPrototype not in modelXbrl.baseSets[baseSetKey]: # only one link per linkrole
                        if relHasFromFactsInTarget:
                            modelXbrl.baseSets[baseSetKey].append(linkPrototype)
                for fromId in fromLabels:
                    if fromId not in linkModelLocIds[linkrole] and relHasFromFactsInTarget and fromId in factsByFactID:
                        linkModelLocIds[linkrole].add(fromId)
                        locPrototype = LocPrototype(factsByFactID[fromId].modelDocument, linkPrototype, fromId, fromId, sourceElement=modelInlineRel)
                        linkPrototype.childElements.append(locPrototype)
                        linkPrototype.labeledResources[fromId].append(locPrototype)
                toLabels = set()
                toFootnoteIds = set()
                toFactQnames = set()
                fromToMatchedIds = set()
                toIdsNotFound = []
                for toId in modelInlineRel.get("toRefs","").split():
                    if toId in modelInlineFootnotesById:
                        toLabels.add(toId)
                        toFootnoteIds.add(toId)
                        if relHasFromFactsInTarget:
                            modelInlineFootnote = modelInlineFootnotesById[toId]
                            if toId not in linkModelInlineFootnoteIds[linkrole]:
                                linkPrototype.childElements.append(modelInlineFootnote)
                                linkModelInlineFootnoteIds[linkrole].add(toId)
                                linkPrototype.labeledResources[toId].append(modelInlineFootnote)
                                relHasToObjectsInTarget = True
                    elif toId in factsByFactID:
                        toLabels.add(toId)
                        if toId not in linkModelLocIds[linkrole]:
                            modelInlineFact = factsByFactID[toId]
                            if relHasFromFactsInTarget and modelInlineFact.get("target") != ixdsTarget:
                                # copy fact to target when not there
                                if ixdsTarget:
                                    modelInlineFact.set("target", ixdsTarget)
                                else:
                                    modelInlineFact.attrib.pop("target", None)
                                addItemFactToTarget(modelInlineFact)
                                locateFactInTuple(modelInlineFact, tuplesByTupleID, modelInlineFact.modelDocument.ixNStag)
                            if modelInlineFact.get("target") == ixdsTarget:
                                linkModelLocIds[linkrole].add(toId)
                                locPrototype = LocPrototype(factsByFactID[toId].modelDocument, linkPrototype, toId, toId, sourceElement=modelInlineRel)
                                toFactQnames.add(str(locPrototype.dereference().qname))
                                linkPrototype.childElements.append(locPrototype)
                                linkPrototype.labeledResources[toId].append(locPrototype)
                                relHasToObjectsInTarget = True
                    else:
                        toIdsNotFound.append(toId)
                    if toId in fromLabels:
                        fromToMatchedIds.add(toId)
                if relHasFromFactsInTarget and relHasToObjectsInTarget:
                    modelXbrl.targetRelationships.add(modelInlineRel)
                if toIdsNotFound:
                    modelXbrl.error(ixMsgCode("relationshipToRef", ns=XbrlConst.ixbrl11, name="relationship", sect="validation"),
                                    _("Inline relationship toRef(s) %(toIds)s not found."),
                                    modelObject=modelInlineRel, toIds=', '.join(sorted(toIdsNotFound)))
                if fromToMatchedIds:
                    modelXbrl.error(ixMsgCode("relationshipFromToMatch", ns=XbrlConst.ixbrl11, name="relationship", sect="validation"),
                                    _("Inline relationship has matching values in fromRefs and toRefs: %(fromToMatchedIds)s"),
                                    modelObject=modelInlineRel, fromToMatchedIds=', '.join(sorted(fromToMatchedIds)))
                for fromLabel in fromLabels:
                    for toLabel in toLabels: # toLabels is empty if no to fact or footnote is in target
                        linkPrototype.childElements.append(ArcPrototype(modelIxdsDocument, linkPrototype, XbrlConst.qnLinkFootnoteArc,
                                                                        fromLabel, toLabel,
                                                                        linkrole, arcrole,
                                                                        modelInlineRel.get("order", "1"), sourceElement=modelInlineRel))
                if toFootnoteIds and toFactQnames:
                    modelXbrl.error(ixMsgCode("relationshipReferencesMixed", ns=XbrlConst.ixbrl11, name="relationship", sect="validation"),
                                    _("Inline relationship references footnote(s) %(toFootnoteIds)s and thereby is not allowed to reference %(toFactQnames)s."),
                                    modelObject=modelInlineRel, toFootnoteIds=', '.join(sorted(toFootnoteIds)),
                                    toFactQnames=', '.join(sorted(toFactQnames)))

    del modelInlineFootnotesById, linkPrototypes, linkModelInlineFootnoteIds # dereference

    # check for multiple use of continuation reference (same continuationAt on different elements)
    for _contAt, _contReferences in continuationReferences.items():
        if len(_contReferences) > 1:
            _refEltQnames = set(str(_contRef.elementQname) for _contRef in _contReferences)
            modelXbrl.error(ixMsgCode("continuationReferences", ns=XbrlConst.ixbrl11, name="continuation", sect="validation"),
                            _("continuedAt %(continuedAt)s has %(referencesCount)s references on %(sourceElements)s elements, only one reference allowed."),
                            modelObject=_contReferences, continuedAt=_contAt, referencesCount=len(_contReferences),
                            sourceElements=', '.join(str(qn) for qn in sorted(_refEltQnames)))

    # check for orphan or mis-located continuation elements
    for _contAt, _contElt in continuationElements.items():
        if _contAt not in continuationReferences:
            modelXbrl.error(ixMsgCode("continuationNotReferenced", ns=XbrlConst.ixbrl11, name="continuation", sect="validation"),
                            _("ix:continuation %(continuedAt)s is not referenced by a, ix:footnote, ix:nonNumeric or other ix:continuation element."),
                            modelObject=_contElt, continuedAt=_contAt)
        if XmlUtil.ancestor(_contElt, _contElt.modelDocument.ixNS, "hidden") is not None:
            modelXbrl.error(ixMsgCode("ancestorNodeDisallowed", ns=XbrlConst.ixbrl11, name="continuation", sect="constraint"),
                            _("ix:continuation %(continuedAt)s may not be nested in an ix:hidden element."),
                            modelObject=_contElt, continuedAt=_contAt)

    if ixdsTarget in modelXbrl.ixTargetRootElements:
        modelIxdsDocument.targetXbrlRootElement = modelXbrl.ixTargetRootElements[ixdsTarget]
        modelIxdsDocument.targetXbrlElementTree = PrototypeElementTree(modelIxdsDocument.targetXbrlRootElement)

    targetDiscoveryCompleted(modelXbrl, modelIxdsDocument)
    for pluginMethod in pluginClassMethods("ModelDocument.IxdsTargetDiscovered"):
        pluginMethod(modelXbrl, modelIxdsDocument)


def loadDTS(modelXbrl, modelIxdsDocument):
    for htmlElt in modelXbrl.ixdsHtmlElements:
        for ixRefElt in htmlElt.iterdescendants(tag=htmlElt.modelDocument.ixNStag + "references"):
            if ixRefElt.get("target") == modelXbrl.ixdsTarget:
                modelIxdsDocument.schemaLinkbaseRefsDiscover(ixRefElt)
                xmlValidate(modelXbrl, ixRefElt) # validate instance elements


def selectTargetDocument(modelXbrl, modelIxdsDocument):
    if not hasattr(modelXbrl, "ixdsTarget"): # DTS discoverey deferred until all ix docs loaded
        # isolate any documents to separate IXDSes according to authority submission rules
        modelXbrl.targetIXDSesToLoad = [] # [[target,[ixdsHtmlElements], ...]
        for pluginXbrlMethod in pluginClassMethods('InlineDocumentSet.IsolateSeparateIXDSes'):
            separateIXDSesHtmlElements = pluginXbrlMethod(modelXbrl)
            if len(separateIXDSesHtmlElements) > 1: # [[ixdsHtml1, ixdsHtml2], [ixdsHtml3...] ...]
                for separateIXDSHtmlElements in separateIXDSesHtmlElements[1:]:
                    toLoadIXDS = [_ixdsTargets(separateIXDSHtmlElements),[]]
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
        _targets = _ixdsTargets(modelXbrl.ixdsHtmlElements)
        if len(_targets) == 0:
            _target = DEFAULT_TARGET
        elif len(_targets) == 1:
            _target = _targets[0]
        elif modelXbrl.modelManager.cntlr.hasGui:
            if True: # provide option to load all or ask user which target
                modelXbrl.targetIXDSesToLoad.insert(0, [_targets[1:],modelXbrl.ixdsHtmlElements])
                _target = _targets[0]
            else: # ask user which target
                dlg = IxdsTargetChoiceDialog(modelXbrl.modelManager.cntlr.parent, _targets)
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


def targetDiscoveryCompleted(modelXbrl, modelIxdsDocument):
    targetIXDSesToLoad = getattr(modelXbrl, "targetIXDSesToLoad", [])
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
        if referencedDoc.type == DocumentType.SCHEMA:
            modelIxdsDocument.targetDocumentSchemaRefs.add(modelIxdsDocument.relativeUri(referencedDoc.uri))
