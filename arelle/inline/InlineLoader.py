"""
See COPYRIGHT.md for copyright information.
"""
import os

from arelle import ModelDocument, ModelXbrl
from arelle.ModelDocument import Type, ModelDocumentReference, inlineIxdsDiscover
from arelle.PluginManager import pluginClassMethods
from arelle.UrlUtil import isHttpUrl
from arelle.inline import DEFAULT_TARGET, IXDS_SURROGATE, IXDS_DOC_SEPARATOR, loadDTS
from arelle.inline.ModelInlineXbrlDocumentSet import ModelInlineXbrlDocumentSet


def _ixdsTargets(ixdsHtmlElements):
    return sorted(set(elt.get("target", DEFAULT_TARGET)
                      for htmlElt in ixdsHtmlElements
                      for elt in htmlElt.iterfind(f".//{{{htmlElt.modelDocument.ixNS}}}references")))


def discoverInlineXbrlDocumentSet(modelDocument, *args, **kwargs):
    if isinstance(modelDocument, ModelInlineXbrlDocumentSet):
        return modelDocument.discoverInlineXbrlDocumentSet()
    return False  # not discoverable by this plug-in


def identifyInlineXbrlDocumentSet(modelXbrl, rootNode, filepath):
    for manifestElt in rootNode.iter(tag="{http://disclosure.edinet-fsa.go.jp/2013/manifest}manifest"):
        # it's an edinet fsa manifest of an inline XBRL document set
        return (Type.INLINEXBRLDOCUMENTSET, ModelInlineXbrlDocumentSet, manifestElt)
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
        ixdocset = ModelDocument.create(modelXbrl, Type.INLINEXBRLDOCUMENTSET, docsetUrl, isEntry=True, initialXml="".join(xml))
        ixdocset.type = Type.INLINEXBRLDOCUMENTSET
        ixdocset.targetDocumentPreferredFilename = None # possibly no inline docs in this doc set
        for i, elt in enumerate(ixdocset.xmlRootElement.iter(tag="instance")):
            # load ix document
            if ixdocs:
                ixdoc = ixdocs[i]
            else:
                ixdoc = ModelDocument.load(modelXbrl, elt.text, referringElement=elt, isDiscovered=True)
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
        if referencedDoc.type == Type.SCHEMA:
            modelIxdsDocument.targetDocumentSchemaRefs.add(modelIxdsDocument.relativeUri(referencedDoc.uri))
