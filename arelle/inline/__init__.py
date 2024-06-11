"""
See COPYRIGHT.md for copyright information.
"""
from optparse import SUPPRESS_HELP

from arelle import ValidateDuplicateFacts


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
