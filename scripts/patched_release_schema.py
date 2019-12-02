import json
import sys

from ocdsextensionregistry import ExtensionRegistry, ProfileBuilder
from ocdsextensionregistry.util import get_latest_version

builder = ProfileBuilder('1__1__4', {
    'additionalContactPoint': 'master',
    'bids': 'master',
    'charges': 'master',
    'finance': 'master',
    'location': 'master',
    'lots': 'master',
    'participation_fee': 'master',
    'partyScale': 'master',
    'process_title': 'master',
})

schema = builder.patched_release_schema(extension_field='extension')

# TODO: Uncomment extensions once PRs merged.
builder = ProfileBuilder('1__1__4', [
    'https://github.com/open-contracting-extensions/ocds_awardCriteria_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_bidOpening_extension/archive/master.zip',
    # 'https://github.com/open-contracting-extensions/ocds_communication_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_contractTerms_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_coveredBy_extension/archive/master.zip',
    # 'https://github.com/open-contracting-extensions/ocds_eu_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_options_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_otherRequirements_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_organizationClassification_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_procedure_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_secondStageDescription_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_selectionCriteria_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_subcontracting_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_submissionTerms_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_techniques_extension/archive/master.zip',
])

schema = builder.patched_release_schema(extension_field='extension', schema=schema)
json.dump(schema, sys.stdout, ensure_ascii=False, indent=2, separators=(',', ': '))
