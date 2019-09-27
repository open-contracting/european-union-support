import json
import sys

from ocdsextensionregistry import ExtensionRegistry, ProfileBuilder
from ocdsextensionregistry.util import get_latest_version

extensions = {}

url = 'https://raw.githubusercontent.com/open-contracting/extension_registry/master/extension_versions.csv'
for version in ExtensionRegistry(url):
    if version.id == 'ppp':  # PPP extension deletes core fields
        continue
    if version.id not in extensions:
        extensions[version.id] = []
    extensions[version.id].append(version)

urls = [get_latest_version(versions).download_url for versions in extensions.values()]

# TODO: Uncomment extensions once PRs merged.
builder = ProfileBuilder('1__1__4', urls + [
    'https://github.com/open-contracting-extensions/ocds_awardCriteria_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_bidOpening_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_contractTerms_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_coveredBy_extension/archive/master.zip',
    # 'https://github.com/open-contracting-extensions/ocds_eu_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_options_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_otherRequirements_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_procedure_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_secondStageDescription_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_selectionCriteria_extension/archive/master.zip',
    # 'https://github.com/open-contracting-extensions/ocds_subcontracting_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_submissionTerms_extension/archive/master.zip',
    'https://github.com/open-contracting-extensions/ocds_techniques_extension/archive/master.zip',
])

schema = builder.patched_release_schema(extension_field='extension')
json.dump(schema, sys.stdout, ensure_ascii=False, indent=2, separators=(',', ': '))
