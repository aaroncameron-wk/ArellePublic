"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

import regex as re

from arelle import XbrlConst
from arelle.ModelValue import QName, qname

browserMaxBase64ImageLength = 5242880  # 5MB

esefTaxonomyNamespaceURIs = frozenset((
    "http://xbrl.ifrs.org/taxonomy/20",
))

disallowedURIsPattern = re.compile(
    "http://xbrl.ifrs.org/taxonomy/[0-9-]{10}/full_ifrs/full_ifrs-cor_[0-9-]{10}[.]xsd|"
    "http://www.esma.europa.eu/taxonomy/[0-9-]{10}/esef_all.xsd"
)


DefaultDimensionLinkroles = (
    "http://www.esma.europa.eu/xbrl/role/cor/ifrs-dim_role-990000",
)

LineItemsNotQualifiedLinkrole = (
    "http://www.esma.europa.eu/xbrl/role/cor/esef_role-999999"
)

qnDomainItemTypes = frozenset((
    qname("{http://www.xbrl.org/dtr/type/non-numeric}nonnum:domainItemType"),
    qname("{http://www.xbrl.org/dtr/type/2020-01-21}nonnum:domainItemType"),
))

linkbaseRefTypes = {
    "http://www.xbrl.org/2003/role/calculationLinkbaseRef": "cal",
    "http://www.xbrl.org/2003/role/definitionLinkbaseRef": "def",
    "http://www.xbrl.org/2003/role/labelLinkbaseRef": "lab",
    "http://www.xbrl.org/2003/role/presentationLinkbaseRef": "pre",
    "http://www.xbrl.org/2003/role/referenceLinkbaseRef": "ref",
}

filenamePatterns = {
    "cal": "{base}-{date}_cal.xml",
    "def": "{base}-{date}_def.xml",
    "lab": "{base}-{date}_lab-{lang}.xml",
    "pre": "{base}-{date}_pre.xml",
    "ref": "{base}-{date}_ref.xml",
}

filenameRegexes = {
    "cal": r"(.{1,})-[0-9]{4}-[0-9]{2}-[0-9]{2}_cal[.]xml$",
    "def": r"(.{1,})-[0-9]{4}-[0-9]{2}-[0-9]{2}_def[.]xml$",
    "lab": r"(.{1,})-[0-9]{4}-[0-9]{2}-[0-9]{2}_lab-[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*[.]xml$",
    "pre": r"(.{1,})-[0-9]{4}-[0-9]{2}-[0-9]{2}_pre[.]xml$",
    "ref": r"(.{1,})-[0-9]{4}-[0-9]{2}-[0-9]{2}_ref[.]xml$",
}

mandatory: set[QName] = set()  # mandatory element qnames

# hidden references
untransformableTypes = frozenset((
    "anyURI",
    "base64Binary",
    "hexBinary",
    "NOTATION",
    "QName",
    "time",
    "token",
    "language",
))

esefDefinitionArcroles = frozenset((
    XbrlConst.all,
    XbrlConst.notAll,
    XbrlConst.hypercubeDimension,
    XbrlConst.dimensionDomain,
    XbrlConst.domainMember,
    XbrlConst.dimensionDefault,
    XbrlConst.widerNarrower,
))

esefPrimaryStatementPlaceholderNames = (
    # to be augmented with future IFRS releases as they come known, as well as further PFS placeholders
    "StatementOfFinancialPositionAbstract",
    "IncomeStatementAbstract",
    "StatementOfComprehensiveIncomeAbstract",
    "StatementOfCashFlowsAbstract",
    "StatementOfChangesInEquityAbstract",
    "StatementOfChangesInNetAssetsAvailableForBenefitsAbstract",
    "StatementOfProfitOrLossAndOtherComprehensiveIncomeAbstract",
)

esefStatementsOfMonetaryDeclarationNames = frozenset((
    # from Annex II para 1
    "StatementOfFinancialPositionAbstract",
    "StatementOfProfitOrLossAndOtherComprehensiveIncomeAbstract"
    "StatementOfChangesInEquityAbstract",
    "StatementOfCashFlowsAbstract",
))

esefMandatoryElementNames2020 = (
    "NameOfReportingEntityOrOtherMeansOfIdentification",
    "ExplanationOfChangeInNameOfReportingEntityOrOtherMeansOfIdentificationFromEndOfPrecedingReportingPeriod",
    "DomicileOfEntity",
    "LegalFormOfEntity",
    "CountryOfIncorporation",
    "AddressOfRegisteredOfficeOfEntity",
    "PrincipalPlaceOfBusiness",
    "DescriptionOfNatureOfEntitysOperationsAndPrincipalActivities",
    "NameOfParentEntity",
    "NameOfUltimateParentOfGroup",
)

esefMandatoryElementNames2022 = (
    "AddressOfRegisteredOfficeOfEntity",
    "CountryOfIncorporation",
    "DescriptionOfAccountingPolicyForAvailableforsaleFinancialAssetsExplanatory",
    "DescriptionOfAccountingPolicyForBiologicalAssetsExplanatory",
    "DescriptionOfAccountingPolicyForBorrowingCostsExplanatory",
    "DescriptionOfAccountingPolicyForBorrowingsExplanatory",
    "DescriptionOfAccountingPolicyForBusinessCombinationsExplanatory",
    "DescriptionOfAccountingPolicyForBusinessCombinationsAndGoodwillExplanatory",
    "DescriptionOfAccountingPolicyForCashFlowsExplanatory",
    "DescriptionOfAccountingPolicyForCollateralExplanatory",
    "DescriptionOfAccountingPolicyForConstructionInProgressExplanatory",
    "DescriptionOfAccountingPolicyForContingentLiabilitiesAndContingentAssetsExplanatory",
    "DescriptionOfAccountingPolicyForCustomerAcquisitionCostsExplanatory",
    "DescriptionOfAccountingPolicyForCustomerLoyaltyProgrammesExplanatory",
    "DescriptionOfAccountingPolicyForDecommissioningRestorationAndRehabilitationProvisionsExplanatory",
    "DescriptionOfAccountingPolicyForDeferredAcquisitionCostsArisingFromInsuranceContractsExplanatory",
    "DescriptionOfAccountingPolicyForDeferredIncomeTaxExplanatory",
    "DescriptionOfAccountingPolicyForDepreciationExpenseExplanatory",
    "DescriptionOfAccountingPolicyForDerecognitionOfFinancialInstrumentsExplanatory",
    "DescriptionOfAccountingPolicyForDerivativeFinancialInstrumentsExplanatory",
    "DescriptionOfAccountingPolicyForDerivativeFinancialInstrumentsAndHedgingExplanatory",
    "DescriptionOfAccountingPolicyToDetermineComponentsOfCashAndCashEquivalents",
    "DescriptionOfAccountingPolicyForDiscontinuedOperationsExplanatory",
    "DescriptionOfAccountingPolicyForDiscountsAndRebatesExplanatory",
    "DescriptionOfAccountingPolicyForDividendsExplanatory",
    "DescriptionOfAccountingPolicyForEarningsPerShareExplanatory",
    "DescriptionOfAccountingPolicyForEmissionRightsExplanatory",
    "DescriptionOfAccountingPolicyForEmployeeBenefitsExplanatory",
    "DescriptionOfAccountingPolicyForEnvironmentRelatedExpenseExplanatory",
    "DescriptionOfAccountingPolicyForExceptionalItemsExplanatory",
    "DescriptionOfAccountingPolicyForExpensesExplanatory",
    "DescriptionOfAccountingPolicyForExplorationAndEvaluationExpenditures",
    "DescriptionOfAccountingPolicyForFairValueMeasurementExplanatory",
    "DescriptionOfAccountingPolicyForFeeAndCommissionIncomeAndExpenseExplanatory",
    "DescriptionOfAccountingPolicyForFinanceCostsExplanatory",
    "DescriptionOfAccountingPolicyForFinanceIncomeAndCostsExplanatory",
    "DescriptionOfAccountingPolicyForFinancialAssetsExplanatory",
    "DescriptionOfAccountingPolicyForFinancialGuaranteesExplanatory",
    "DescriptionOfAccountingPolicyForFinancialInstrumentsExplanatory",
    "DescriptionOfAccountingPolicyForFinancialInstrumentsAtFairValueThroughProfitOrLossExplanatory",
    "DescriptionOfAccountingPolicyForFinancialLiabilitiesExplanatory",
    "DescriptionOfAccountingPolicyForForeignCurrencyTranslationExplanatory",
    "DescriptionOfAccountingPolicyForFranchiseFeesExplanatory",
    "DescriptionOfAccountingPolicyForFunctionalCurrencyExplanatory",
    "DescriptionOfAccountingPolicyForGoodwillExplanatory",
    "DescriptionOfAccountingPolicyForGovernmentGrants",
    "DescriptionOfAccountingPolicyForHedgingExplanatory",
    "DescriptionOfAccountingPolicyForHeldtomaturityInvestmentsExplanatory",
    "DescriptionOfAccountingPolicyForImpairmentOfAssetsExplanatory",
    "DescriptionOfAccountingPolicyForImpairmentOfFinancialAssetsExplanatory",
    "DescriptionOfAccountingPolicyForImpairmentOfNonfinancialAssetsExplanatory",
    "DescriptionOfAccountingPolicyForIncomeTaxExplanatory",
    "DescriptionOfAccountingPolicyForInsuranceContracts",
    "DescriptionOfAccountingPolicyForIntangibleAssetsAndGoodwillExplanatory",
    "DescriptionOfAccountingPolicyForIntangibleAssetsOtherThanGoodwillExplanatory",
    "DescriptionOfAccountingPolicyForInterestIncomeAndExpenseExplanatory",
    "DescriptionOfAccountingPolicyForInvestmentInAssociates",
    "DescriptionOfAccountingPolicyForInvestmentInAssociatesAndJointVenturesExplanatory",
    "DescriptionOfAccountingPolicyForInvestmentPropertyExplanatory",
    "DescriptionOfAccountingPolicyForInvestmentsInJointVentures",
    "DescriptionOfAccountingPolicyForInvestmentsOtherThanInvestmentsAccountedForUsingEquityMethodExplanatory",
    "DescriptionOfAccountingPolicyForIssuedCapitalExplanatory",
    "DescriptionOfAccountingPolicyForLeasesExplanatory",
    "DescriptionOfAccountingPolicyForLoansAndReceivablesExplanatory",
    "DescriptionOfAccountingPolicyForMeasuringInventories",
    "DescriptionOfAccountingPolicyForMiningAssetsExplanatory",
    "DescriptionOfAccountingPolicyForMiningRightsExplanatory",
    "DescriptionOfAccountingPolicyForNoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleExplanatory",
    "DescriptionOfAccountingPolicyForNoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleAndDiscontinuedOperationsExplanatory",
    "DescriptionOfAccountingPolicyForOffsettingOfFinancialInstrumentsExplanatory",
    "DescriptionOfAccountingPolicyForOilAndGasAssetsExplanatory",
    "DescriptionOfAccountingPolicyForProgrammingAssetsExplanatory",
    "DescriptionOfAccountingPolicyForPropertyPlantAndEquipmentExplanatory",
    "DescriptionOfAccountingPolicyForProvisionsExplanatory",
    "DescriptionOfAccountingPolicyForReclassificationOfFinancialInstrumentsExplanatory",
    "DescriptionOfAccountingPolicyForRecognisingDifferenceBetweenFairValueAtInitialRecognitionAndAmountDeterminedUsingValuationTechniqueExplanatory",
    "DescriptionOfAccountingPolicyForRecognitionOfRevenue",
    "DescriptionOfAccountingPolicyForRegulatoryDeferralAccountsExplanatory",
    "DescriptionOfAccountingPolicyForReinsuranceExplanatory",
    "DescriptionOfAccountingPolicyForRepairsAndMaintenanceExplanatory",
    "DescriptionOfAccountingPolicyForRepurchaseAndReverseRepurchaseAgreementsExplanatory",
    "DescriptionOfAccountingPolicyForResearchAndDevelopmentExpenseExplanatory",
    "DescriptionOfAccountingPolicyForRestrictedCashAndCashEquivalentsExplanatory",
    "DescriptionOfAccountingPolicyForSegmentReportingExplanatory",
    "DescriptionOfAccountingPolicyForServiceConcessionArrangementsExplanatory",
    "DescriptionOfAccountingPolicyForSharebasedPaymentTransactionsExplanatory",
    "DescriptionOfAccountingPolicyForStrippingCostsExplanatory",
    "DescriptionOfAccountingPolicyForSubsidiariesExplanatory",
    "DescriptionOfAccountingPolicyForTaxesOtherThanIncomeTaxExplanatory",
    "DescriptionOfAccountingPolicyForTerminationBenefits",
    "DescriptionOfAccountingPolicyForTradeAndOtherPayablesExplanatory",
    "DescriptionOfAccountingPolicyForTradeAndOtherReceivablesExplanatory",
    "DescriptionOfAccountingPolicyForTradingIncomeAndExpenseExplanatory",
    "DescriptionOfAccountingPolicyForTransactionsWithNoncontrollingInterestsExplanatory",
    "DescriptionOfAccountingPolicyForTransactionsWithRelatedPartiesExplanatory",
    "DescriptionOfAccountingPolicyForTreasurySharesExplanatory",
    "DescriptionOfAccountingPolicyForWarrantsExplanatory",
    "DescriptionOfReasonWhyFinancialStatementsAreNotEntirelyComparable",
    "DescriptionOfNatureOfEntitysOperationsAndPrincipalActivities",
    "DescriptionOfOtherAccountingPoliciesRelevantToUnderstandingOfFinancialStatements",
    "DescriptionOfReasonForUsingLongerOrShorterReportingPeriod",
    "DisclosureOfAccountingJudgementsAndEstimatesExplanatory",
    "DisclosureOfAccruedExpensesAndOtherLiabilitiesExplanatory",
    "DisclosureOfAllowanceForCreditLossesExplanatory",
    "DisclosureOfAssetsAndLiabilitiesWithSignificantRiskOfMaterialAdjustmentExplanatory",
    "DisclosureOfSignificantInvestmentsInAssociatesExplanatory",
    "DisclosureOfAuditorsRemunerationExplanatory",
    "DisclosureOfAuthorisationOfFinancialStatementsExplanatory",
    "DisclosureOfAvailableforsaleAssetsExplanatory",
    "DisclosureOfBasisOfConsolidationExplanatory",
    "DisclosureOfBasisOfPreparationOfFinancialStatementsExplanatory",
    "DisclosureOfBiologicalAssetsAndGovernmentGrantsForAgriculturalActivityExplanatory",
    "DisclosureOfBorrowingsExplanatory",
    "DisclosureOfBusinessCombinationsExplanatory",
    "DisclosureOfCashAndBankBalancesAtCentralBanksExplanatory",
    "DisclosureOfCashAndCashEquivalentsExplanatory",
    "DisclosureOfCashFlowStatementExplanatory",
    "DisclosureOfChangesInAccountingPoliciesExplanatory",
    "DisclosureOfChangesInAccountingPoliciesAccountingEstimatesAndErrorsExplanatory",
    "DisclosureOfClaimsAndBenefitsPaidExplanatory",
    "DisclosureOfCollateralExplanatory",
    "DisclosureOfCommitmentsExplanatory",
    "DisclosureOfCommitmentsAndContingentLiabilitiesExplanatory",
    "DisclosureOfContingentLiabilitiesExplanatory",
    "DisclosureOfCostOfSalesExplanatory",
    "DisclosureOfCreditRiskExplanatory",
    "DisclosureOfDebtSecuritiesExplanatory",
    "DisclosureOfDeferredAcquisitionCostsArisingFromInsuranceContractsExplanatory",
    "DisclosureOfDeferredIncomeExplanatory",
    "DisclosureOfDeferredTaxesExplanatory",
    "DisclosureOfDepositsFromBanksExplanatory",
    "DisclosureOfDepositsFromCustomersExplanatory",
    "DisclosureOfDepreciationAndAmortisationExpenseExplanatory",
    "DisclosureOfDerivativeFinancialInstrumentsExplanatory",
    "DisclosureOfDiscontinuedOperationsExplanatory",
    "DisclosureOfDividendsExplanatory",
    "DisclosureOfEarningsPerShareExplanatory",
    "DisclosureOfEffectOfChangesInForeignExchangeRatesExplanatory",
    "DisclosureOfEmployeeBenefitsExplanatory",
    "DisclosureOfEntitysReportableSegmentsExplanatory",
    "DisclosureOfEventsAfterReportingPeriodExplanatory",
    "DisclosureOfExpensesExplanatory",
    "DisclosureOfExpensesByNatureExplanatory",
    "DisclosureOfExplorationAndEvaluationAssetsExplanatory",
    "DisclosureOfFairValueMeasurementExplanatory",
    "DisclosureOfFairValueOfFinancialInstrumentsExplanatory",
    "DisclosureOfFeeAndCommissionIncomeExpenseExplanatory",
    "DisclosureOfFinanceCostExplanatory",
    "DisclosureOfFinanceIncomeExpenseExplanatory",
    "DisclosureOfFinanceIncomeExplanatory",
    "DisclosureOfFinancialAssetsHeldForTradingExplanatory",
    "DisclosureOfFinancialInstrumentsExplanatory",
    "DisclosureOfFinancialInstrumentsAtFairValueThroughProfitOrLossExplanatory",
    "DisclosureOfFinancialInstrumentsDesignatedAtFairValueThroughProfitOrLossExplanatory",
    "DisclosureOfFinancialInstrumentsHeldForTradingExplanatory",
    "DisclosureOfFinancialLiabilitiesHeldForTradingExplanatory",
    "DisclosureOfFinancialRiskManagementExplanatory",
    "DisclosureOfFirstTimeAdoptionExplanatory",
    "DisclosureOfGeneralAndAdministrativeExpenseExplanatory",
    "DisclosureOfGeneralInformationAboutFinancialStatementsExplanatory",
    "DisclosureOfGoingConcernExplanatory",
    "DisclosureOfGoodwillExplanatory",
    "DisclosureOfGovernmentGrantsExplanatory",
    "DisclosureOfImpairmentOfAssetsExplanatory",
    "DisclosureOfIncomeTaxExplanatory",
    "DisclosureOfInformationAboutEmployeesExplanatory",
    "DisclosureOfInformationAboutKeyManagementPersonnelExplanatory",
    "DisclosureOfInsuranceContractsExplanatory",
    "DisclosureOfInsurancePremiumRevenueExplanatory",
    "DisclosureOfIntangibleAssetsExplanatory",
    "DisclosureOfIntangibleAssetsAndGoodwillExplanatory",
    "DisclosureOfInterestExpenseExplanatory",
    "DisclosureOfInterestIncomeExpenseExplanatory",
    "DisclosureOfInterestIncomeExplanatory",
    "DisclosureOfInventoriesExplanatory",
    "DisclosureOfInvestmentContractsLiabilitiesExplanatory",
    "DisclosureOfInvestmentPropertyExplanatory",
    "DisclosureOfInvestmentsAccountedForUsingEquityMethodExplanatory",
    "DisclosureOfInvestmentsOtherThanInvestmentsAccountedForUsingEquityMethodExplanatory",
    "DisclosureOfIssuedCapitalExplanatory",
    "DisclosureOfJointVenturesExplanatory",
    "DisclosureOfLeasePrepaymentsExplanatory",
    "DisclosureOfLeasesExplanatory",
    "DisclosureOfLiquidityRiskExplanatory",
    "DisclosureOfLoansAndAdvancesToBanksExplanatory",
    "DisclosureOfLoansAndAdvancesToCustomersExplanatory",
    "DisclosureOfMarketRiskExplanatory",
    "DisclosureOfNetAssetValueAttributableToUnitholdersExplanatory",
    "DisclosureOfNoncontrollingInterestsExplanatory",
    "DisclosureOfNoncurrentAssetsHeldForSaleAndDiscontinuedOperationsExplanatory",
    "DisclosureOfNoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleExplanatory",
    "DisclosureOfObjectivesPoliciesAndProcessesForManagingCapitalExplanatory",
    "DisclosureOfOtherAssetsExplanatory",
    "DisclosureOfOtherCurrentAssetsExplanatory",
    "DisclosureOfOtherCurrentLiabilitiesExplanatory",
    "DisclosureOfOtherLiabilitiesExplanatory",
    "DisclosureOfOtherNoncurrentAssetsExplanatory",
    "DisclosureOfOtherNoncurrentLiabilitiesExplanatory",
    "DisclosureOfOtherOperatingExpenseExplanatory",
    "DisclosureOfOtherOperatingIncomeExpenseExplanatory",
    "DisclosureOfOtherOperatingIncomeExplanatory",
    "DisclosureOfPrepaymentsAndOtherAssetsExplanatory",
    "DisclosureOfProfitLossFromOperatingActivitiesExplanatory",
    "DisclosureOfPropertyPlantAndEquipmentExplanatory",
    "DisclosureOfOtherProvisionsExplanatory",
    "DisclosureOfReclassificationOfFinancialInstrumentsExplanatory",
    "DisclosureOfReclassificationsOrChangesInPresentationExplanatory",
    "DisclosureOfRecognisedRevenueFromConstructionContractsExplanatory"
    "DisclosureOfReinsuranceExplanatory",
    "DisclosureOfRelatedPartyExplanatory",
    "DisclosureOfRepurchaseAndReverseRepurchaseAgreementsExplanatory",
    "DisclosureOfResearchAndDevelopmentExpenseExplanatory",
    "DisclosureOfReservesAndOtherEquityInterestExplanatory",
    "DisclosureOfRestrictedCashAndCashEquivalentsExplanatory",
    "DisclosureOfRevenueExplanatory",
    "DisclosureOfServiceConcessionArrangementsExplanatory",
    "DisclosureOfShareCapitalReservesAndOtherEquityInterestExplanatory",
    "DisclosureOfSharebasedPaymentArrangementsExplanatory",
    "DisclosureOfSummaryOfSignificantAccountingPoliciesExplanatory",
    "DisclosureOfSubordinatedLiabilitiesExplanatory",
    "DisclosureOfSignificantInvestmentsInSubsidiariesExplanatory",
    "DisclosureOfTaxReceivablesAndPayablesExplanatory",
    "DisclosureOfTradeAndOtherPayablesExplanatory",
    "DisclosureOfTradeAndOtherReceivablesExplanatory",
    "DisclosureOfTradingIncomeExpenseExplanatory",
    "DisclosureOfTreasurySharesExplanatory",
    "DescriptionOfUncertaintiesOfEntitysAbilityToContinueAsGoingConcern",
    "DividendsProposedOrDeclaredBeforeFinancialStatementsAuthorisedForIssueButNotRecognisedAsDistributionToOwners",
    "DividendsProposedOrDeclaredBeforeFinancialStatementsAuthorisedForIssueButNotRecognisedAsDistributionToOwnersPerShare",
    "DividendsRecognisedAsDistributionsToOwnersPerShare",
    "DomicileOfEntity",
    "ExplanationOfDepartureFromIFRS",
    "ExplanationOfFactAndBasisForPreparationOfFinancialStatementsWhenNotGoingConcernBasis",
    "ExplanationOfFinancialEffectOfDepartureFromIFRS",
    "ExplanationOfAssumptionAboutFutureWithSignificantRiskOfResultingInMaterialAdjustments",
    "ExplanationWhyFinancialStatementsNotPreparedOnGoingConcernBasis",
    "LegalFormOfEntity",
    "LengthOfLifeOfLimitedLifeEntity",
    "NameOfParentEntity",
    "NameOfReportingEntityOrOtherMeansOfIdentification",
    "NameOfUltimateParentOfGroup",
    "PrincipalPlaceOfBusiness",
    "StatementOfIFRSCompliance",
)

htmlEventHandlerAttributes = frozenset((
    "onabort",
    "onafterprint",
    "onbeforeprint",
    "onbeforeunload",
    "onblur",
    "oncanplay",
    "oncanplaythrough",
    "onchange",
    "onclick",
    "oncontextmenu",
    "oncopy",
    "oncuechange",
    "oncut",
    "ondblclick",
    "ondrag",
    "ondragend",
    "ondragenter",
    "ondragleave",
    "ondragover",
    "ondragstart",
    "ondrop",
    "ondurationchange",
    "onemptied",
    "onended",
    "onerror",
    "onfocus",
    "onhashchange",
    "oninput",
    "oninvalid",
    "onkeydown",
    "onkeypress",
    "onkeyup",
    "onload",
    "onloadeddata",
    "onloadedmetadata",
    "onloadstart",
    "onmessage",
    "onmousedown",
    "onmousemove",
    "onmouseout",
    "onmouseover",
    "onmouseup",
    "onmousewheel",
    "onoffline",
    "ononline",
    "onpagehide",
    "onpageshow",
    "onpaste",
    "onpause",
    "onplay",
    "onplaying",
    "onpopstate",
    "onprogress",
    "onratechange",
    "onreset",
    "onresize",
    "onscroll",
    "onsearch",
    "onseeked",
    "onseeking",
    "onselect",
    "onstalled",
    "onstorage",
    "onsubmit",
    "onsuspend",
    "ontimeupdate",
    "ontoggle",
    "onunload",
    "onvolumechange",
    "onwaiting",
    "onwheel",
))

svgEventAttributes = frozenset((
    "onabort",
    "onactivate",
    "onafterprint",
    "onbeforeprint",
    "onbegin",
    "oncancel",
    "oncanplay",
    "oncanplaythrough",
    "onchange",
    "onclick",
    "onclose",
    "oncopy",
    "oncuechange",
    "oncut",
    "ondblclick",
    "ondrag",
    "ondragend",
    "ondragenter",
    "ondragexit",
    "ondragleave",
    "ondragover",
    "ondragstart",
    "ondrop",
    "ondurationchange",
    "onemptied",
    "onend",
    "onended",
    "onerror",
    "onfocus",
    "onfocusin",
    "onfocusout",
    "onhashchange",
    "oninput",
    "oninvalid",
    "onkeydown",
    "onkeypress",
    "onkeyup",
    "onload",
    "onloadeddata",
    "onloadedmetadata",
    "onloadstart",
    "onmessage",
    "onmousedown",
    "onmouseenter",
    "onmouseleave",
    "onmousemove",
    "onmouseout",
    "onmouseover",
    "onmouseup",
    "onmousewheel",
    "onoffline",
    "ononline",
    "onpagehide",
    "onpageshow",
    "onpaste",
    "onpause",
    "onplay",
    "onplaying",
    "onpopstate",
    "onprogress",
    "onratechange",
    "onrepeat",
    "onreset",
    "onresize",
    "onscroll",
    "onseeked",
    "onseeking",
    "onselect",
    "onshow",
    "onstalled",
    "onstorage",
    "onsubmit",
    "onsuspend",
    "ontimeupdate",
    "ontoggle",
    "onunload",
    "onvolumechange",
    "onwaiting",
    "onzoom",
))
