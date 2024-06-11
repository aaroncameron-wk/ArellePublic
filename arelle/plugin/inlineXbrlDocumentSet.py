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

from arelle.Version import authorLabel, copyrightLabel


__pluginInfo__ = {
    'name': 'Inline XBRL Document Set',
    'version': '1.1',
    'description': "This plug-in adds a feature to read manifest files of inline XBRL document sets "
                    " and to save the embedded XBRL instance document.  "
                    "Support single target instance documents in a single document set.  ",
    'license': 'Apache-2',
    'author': authorLabel,
    'copyright': copyrightLabel,
}
