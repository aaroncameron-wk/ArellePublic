from arelle.ModelObject import ModelObject


class ModelDocumentReference:
    def __init__(self, referenceType, referringModelObject=None):
        self.referenceTypes = {referenceType}
        self.referringModelObject = referringModelObject

    @property
    def referringXlinkRole(self):
        if "href" in self.referenceTypes and isinstance(self.referringModelObject, ModelObject):
            return self.referringModelObject.get("{http://www.w3.org/1999/xlink}role")
        return None
