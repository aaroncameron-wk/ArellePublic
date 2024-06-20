import os

from arelle.DocumentType import DocumentType
from arelle.ModelObject import ModelObject
from arelle.inline.InlineConstants import IXDS_DOC_SEPARATOR, IXDS_SURROGATE, MINIMUM_IXDS_DOC_COUNT

_skipExpectedInstanceComparison = None


def getInlineReadMeFirstUris(modelTestcaseVariation):
    _readMeFirstUris = [os.path.join(modelTestcaseVariation.modelDocument.filepathdir,
                                     (elt.get("{http://www.w3.org/1999/xlink}href") or elt.text).strip())
                        for elt in modelTestcaseVariation.iterdescendants()
                        if isinstance(elt,ModelObject) and elt.get("readMeFirst") == "true"]
    if len(_readMeFirstUris) >= MINIMUM_IXDS_DOC_COUNT and all(
            DocumentType.identify(modelTestcaseVariation.modelXbrl.fileSource, f) == DocumentType.INLINEXBRL for f in _readMeFirstUris):
        docsetSurrogatePath = os.path.join(os.path.dirname(_readMeFirstUris[0]), IXDS_SURROGATE)
        modelTestcaseVariation._readMeFirstUris = [docsetSurrogatePath + IXDS_DOC_SEPARATOR.join(_readMeFirstUris)]
        return True


def setSkipExpectedInstanceComparison(value: bool) -> None:
    global _skipExpectedInstanceComparison
    _skipExpectedInstanceComparison = value


def skipExpectedInstanceComparison():
    global _skipExpectedInstanceComparison
    return bool(_skipExpectedInstanceComparison)
