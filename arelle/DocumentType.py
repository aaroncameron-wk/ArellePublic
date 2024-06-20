from lxml import etree

from arelle import XbrlConst
from arelle.FileSource import FileSource


class DocumentType:
    """
    .. class:: Type

    Static class of Enumerated type representing modelDocument type
    """
    UnknownXML=0
    UnknownNonXML=1
    UnknownTypes=1  # to test if any unknown type, use <= Type.UnknownTypes
    firstXBRLtype=2  # first filetype that is XBRL and can hold a linkbase, etc inside it
    SCHEMA=2
    LINKBASE=3
    INSTANCE=4
    INLINEXBRL=5
    lastXBRLtype=5  # first filetype that is XBRL and can hold a linkbase, etc inside it
    DTSENTRIES=6  # multiple schema/linkbase Refs composing a DTS but not from an instance document
    INLINEXBRLDOCUMENTSET=7
    VERSIONINGREPORT=8
    TESTCASESINDEX=9
    TESTCASE=10
    REGISTRY=11
    REGISTRYTESTCASE=12
    XPATHTESTSUITE=13
    RSSFEED=14
    ARCSINFOSET=15
    FACTDIMSINFOSET=16
    HTML=17

    TESTCASETYPES = (TESTCASESINDEX, TESTCASE, REGISTRY, REGISTRYTESTCASE, XPATHTESTSUITE)

    typeName = ("unknown XML",
                "unknown non-XML",
                "schema",
                "linkbase",
                "instance",
                "inline XBRL instance",
                "entry point set",
                "inline XBRL document set",
                "versioning report",
                "testcases index",
                "testcase",
                "registry",
                "registry testcase",
                "xpath test suite",
                "RSS feed",
                "arcs infoset",
                "fact dimensions infoset",
                "html non-XBRL")

    @staticmethod
    def identify(filesource: FileSource, filepath: str) -> int:
        _type = DocumentType.UnknownNonXML
        _file, = filesource.file(filepath, stripDeclaration=True, binary=True)
        try:
            _rootElt = True
            _maybeHtml = False
            for _event, elt in etree.iterparse(_file, events=("start",), recover=True, huge_tree=True):
                if _rootElt:
                    _rootElt = False
                    _type = {"testcases": DocumentType.TESTCASESINDEX,
                             "documentation": DocumentType.TESTCASESINDEX,
                             "testSuite": DocumentType.TESTCASESINDEX,
                             "registries": DocumentType.TESTCASESINDEX,
                             "testcase": DocumentType.TESTCASE,
                             "testSet": DocumentType.TESTCASE,
                             "rss": DocumentType.RSSFEED
                             }.get(etree.QName(elt).localname)
                    if _type:
                        break
                    _type = {"{http://www.xbrl.org/2003/instance}xbrl": DocumentType.INSTANCE,
                             "{http://www.xbrl.org/2003/linkbase}linkbase": DocumentType.LINKBASE,
                             "{http://www.w3.org/2001/XMLSchema}schema": DocumentType.SCHEMA,
                             "{http://xbrl.org/2008/registry}registry": DocumentType.REGISTRY
                             }.get(elt.tag, DocumentType.UnknownXML)
                    if _type == DocumentType.UnknownXML and elt.tag.endswith("html"):
                        _maybeHtml = True
                    else:
                        break # stop parsing
                if XbrlConst.ixbrlTagPattern.match(elt.tag):
                    _type = DocumentType.INLINEXBRL
                    break
            if _type == DocumentType.UnknownXML and _maybeHtml:
                _type = DocumentType.HTML
        except Exception as err:
            if not _rootElt: # if _rootElt is false then a root element was found and it's some kind of xml
                _type = DocumentType.UnknownXML
                if filesource.cntlr:
                    filesource.cntlr.addToLog("%(error)s",
                                              messageCode="arelle:fileIdentificationError",
                                              messageArgs={"error":err}, file=filepath)
        _file.close()
        return _type
