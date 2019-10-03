import csv
import re
import sys
from glob import glob

subjects = {
    # Unambiguous
    'award': 'awards',
    'contract': 'contracts',
    'lot': 'tender/lots',
    'party': 'parties',
    'release': '',
    'statistic': 'bids/statistics',

    # Ambiguous
    'amendment': {
        'CHANGES': 'tender/amendments',
        'MODIFICATIONS_CONTRACT': 'contracts/amendments',
    },
    'classification': {
        'CONTRACTING_BODY': 'parties/details/classifications',
        'PROCEDURE': 'tender/procurementMethodRationaleCodes',
    },
    'criterion': {
        'LEFTI': 'tender/selectionCriteria/criteria',
        'OBJECT_CONTRACT': 'tender/lots/awardCriteria/criteria',
    },
    'item': {
        'MODIFICATIONS_CONTRACT': 'contracts/items',
        'OBJECT_CONTRACT': 'tender/items',
    },
}

unknowns = {
    # Unambiguous
    '.additionalContactPoints': 'parties',
    '.awardID': 'contracts',
    '.countryCode': 'parties/address',
    '.details.classifications': 'parties',
    '.documentType': 'tender/documents',
    '.financingParty.id': 'planning/budget/finance',
    '.financingParty.name': 'planning/budget/finance',
    '.identifier.id': 'parties',
    '.identifier.legalName': 'parties',
    '.identifier.scheme': 'parties',
    '.measure': 'bids/statistics',  # metrics extension not used
    '.minimum': 'tender/selectionCriteria/criteria',
    '.roles': 'parties',
    '.secondStage.maximumCandidates': 'tender/lots',
    '.secondStage.minimumCandidates': 'tender/lots',
    '.subcontracting.maxPercentage': 'awards',
    '.suppliers': 'awards',  # contract suppliers extension not used

    # Ambiguous
    '.additionalClassifications': {
        'MODIFICATIONS_CONTRACT': 'contracts/items',
    },
    '.description': {
        # Root
        'LEFTI': 'tender/selectionCriteria/criteria',
        # XPath
        '/OBJECT_CONTRACT/OBJECT_DESCR/EU_PROGR_RELATED': 'planning/budget/finance',
    },
    '.id': {
        # Root
        'CHANGES': 'tender/amendments',
        'LEFTI': 'tender/documents',
        'PROCEDURE': 'tender/procurementMethodRationaleCodes',
        # XPath
        '/AWARD_CONTRACT/AWARDED_CONTRACT': 'contracts',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR': 'awards/suppliers',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED': 'bids/statistics',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_EMEANS': 'bids/statistics',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_NON_EU': 'bids/statistics',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_OTHER_EU': 'bids/statistics',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_SME': 'bids/statistics',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/HIGH': 'bids/statistics',
        '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/LOW': 'bids/statistics',
        '/CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY': 'parties',
        '/CONTRACTING_BODY/DOCUMENT_RESTRICTED': 'tender/participationFees',
        '/CONTRACTING_BODY/CA_ACTIVITY': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_ACTIVITY/@VALUE': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_TYPE': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_TYPE/@VALUE': 'parties/details/classifications',
        '/CONTRACTING_BODY/CE_ACTIVITY': 'parties/details/classifications',
        '/CONTRACTING_BODY/CE_ACTIVITY/@VALUE': 'parties/details/classifications',
        '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR': 'awards/suppliers',  # noqa
        '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_ADDITIONAL/CPV_CODE': 'contracts/items/additionalClassifications',  # noqa
        '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE': 'contracts/items/additionalClassifications',  # noqa
        '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE': 'contracts/items/additionalClassifications',  # noqa
        '/MODIFICATIONS_CONTRACT/INFO_MODIFICATIONS': 'contracts/amendments',
        '/OBJECT_CONTRACT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE': 'tender/items/additionalClassifications',
        '/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_CODE': 'tender/items/additionalClassifications',
        '/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE': 'tender/items/additionalClassifications',  # noqa
        '/OBJECT_CONTRACT/OBJECT_DESCR/EU_PROGR_RELATED': 'planning/budget/finance',
        '/OBJECT_CONTRACT/VAL_RANGE_TOTAL/HIGH': 'bids/statistics',
        '/OBJECT_CONTRACT/VAL_RANGE_TOTAL/LOW': 'bids/statistics',
        '/RESULTS/AWARDED_PRIZE': 'contracts',
        '/RESULTS/AWARDED_PRIZE/PARTICIPANTS/NB_PARTICIPANTS': 'bids/statistics',
        '/RESULTS/AWARDED_PRIZE/PARTICIPANTS/NB_PARTICIPANTS_OTHER_EU': 'bids/statistics',
        '/RESULTS/AWARDED_PRIZE/PARTICIPANTS/NB_PARTICIPANTS_SME': 'bids/statistics',
        '/RESULTS/AWARDED_PRIZE/WINNERS/WINNER/ADDRESS_WINNER': 'awards/suppliers',
    },
    '.items': {
        'MODIFICATIONS_CONTRACT': 'contracts',
    },
    '.name': {
        # Root
        'AWARD_CONTRACT': 'awards/suppliers',
        'MODIFICATIONS_CONTRACT': 'awards/suppliers',
        'OBJECT_CONTRACT': 'parties',
        'PROCEDURE': 'tender/procurementMethodRationaleCodes',
        'RESULTS': 'awards/suppliers',
        # XPath
        '/CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY': 'buyer',
        '/CONTRACTING_BODY/CA_ACTIVITY': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_ACTIVITY/@VALUE': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_ACTIVITY_OTHER': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_TYPE': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_TYPE/@VALUE': 'parties/details/classifications',
        '/CONTRACTING_BODY/CA_TYPE_OTHER': 'parties/details/classifications',
        '/CONTRACTING_BODY/CE_ACTIVITY': 'parties/details/classifications',
        '/CONTRACTING_BODY/CE_ACTIVITY/@VALUE': 'parties/details/classifications',
        '/CONTRACTING_BODY/CE_ACTIVITY_OTHER': 'parties/details/classifications',
    },
    '.relatedLot': {
        'AWARD_CONTRACT': 'bids/statistics',
        'RESULTS': 'bids/statistics',
    },
    '.relatedLots': {
        'AWARD_CONTRACT': 'awards',
        'OBJECT_CONTRACT': 'planning/budget/finance',
    },
    '.region': {
        '/OBJECT_CONTRACT/OBJECT_DESCR/NUTS': 'tender/items/deliveryAddresses',
    },
    '.scheme': {
        'MODIFICATIONS_CONTRACT': 'contracts/items/additionalClassifications',
        'OBJECT_CONTRACT': 'tender/items/additionalClassifications',
    },
    '.status': {
        'AWARD_CONTRACT': 'contracts',
        'RESULTS': 'contracts',
    },
    '.title': {
        'AWARD_CONTRACT': 'contracts',
    },
    '.type': {
        # Root
        'CONTRACTING_BODY': 'tender/participationFees',
        'LEFTI': 'tender.selectionCriteria.criteria',
        'OBJECT_CONTRACT': 'tender/lots/awardCriteria/criteria',
    },
    '.value': {
        'AWARD_CONTRACT': 'bids/statistics',
        'OBJECT_CONTRACT': 'bids/statistics',
        'RESULTS': 'bids/statistics',
    },
}

unhandled = set()
paths = set()


def report(path, row):
    value = (path, row.get('xpath'))
    if value not in unhandled:
        sys.stderr.write('unhandled: {} ({}: {})\n'.format(path, row.get('xpath'), row['guidance']))
    unhandled.add(value)


for pattern in ('output/mapping/*.csv', 'output/mapping/*/*.csv'):
    for filename in glob(pattern):
        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('guidance'):
                    for match in re.finditer(r"(?:([a-z]+)'s )?\[?`([^`]+)`", row['guidance']):
                        path = match.group(2)
                        if path in ('true', 'false', 'value'):  # JSON boolean, exceptional case
                            continue
                        if re.search(r'^[A-Z][a-z][A-Za-z]+$', path):  # JSON Schema definition
                            continue
                        if re.search(r'^(/[A-Z_]+)+$', path):  # XPath
                            continue
                        if re.search(r'^[A-Z_]+$', path):  # XML element
                            continue

                        subject = match.group(1)

                        prefix = ''
                        if subject:
                            prefix = subjects[subject]
                        elif path in unknowns:
                            prefix = unknowns[path]
                        elif path[0] == '.':
                            report(path, row)
                            continue

                        if isinstance(prefix, dict):
                            xpath = row.get('xpath', '/')
                            root = xpath.split('/', 2)[1]
                            if root in prefix:
                                key = root
                            else:
                                key = xpath
                            try:
                                prefix = prefix[key]
                            except KeyError:
                                report(path, row)
                                continue

                        path = prefix + path
                        paths.add(path.replace('.', '/'))

with open('scripts/mapping-sheet.csv') as f:
    seen = [row['path'] for row in csv.DictReader(f)]
    for path in sorted(list(paths)):
        if path not in seen:
            print(path)
