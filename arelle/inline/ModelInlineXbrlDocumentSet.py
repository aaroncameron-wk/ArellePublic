"""
See COPYRIGHT.md for copyright information.
"""
from arelle.ModelDocument import ModelDocument, ModelDocumentReference, load


# class representing surrogate object for multi-document inline xbrl document set, references individual ix documents
class ModelInlineXbrlDocumentSet(ModelDocument):

    def discoverInlineXbrlDocumentSet(self):
        # for JP FSA inline document set manifest, acting as document set surrogate entry object, load referenced ix documents
        for instanceElt in self.xmlRootElement.iter(tag="{http://disclosure.edinet-fsa.go.jp/2013/manifest}instance"):
            targetId = instanceElt.id
            self.targetDocumentId = targetId
            self.targetDocumentPreferredFilename = instanceElt.get('preferredFilename')
            for ixbrlElt in instanceElt.iter(tag="{http://disclosure.edinet-fsa.go.jp/2013/manifest}ixbrl"):
                uri = ixbrlElt.textValue.strip()
                if uri:
                    # load ix document
                    doc = load(self.modelXbrl, uri, base=self.filepath, referringElement=instanceElt)
                    if doc is not None and doc not in self.referencesDocument:
                        # set reference to ix document if not in circular reference
                        referencedDocument = ModelDocumentReference("inlineDocument", instanceElt)
                        referencedDocument.targetId = targetId
                        self.referencesDocument[doc] = referencedDocument
                        self.ixNS = doc.ixNS
        return True
