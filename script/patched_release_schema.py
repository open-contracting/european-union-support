import json
import sys

import requests
from ocdsextensionregistry import ProfileBuilder

url = 'https://raw.githubusercontent.com/open-contracting-extensions/european-union/latest/docs/extension_versions.json'  # noqa: E501

builder = ProfileBuilder('1__1__5', requests.get(url).json())

schema = builder.patched_release_schema(extension_field='extension')

json.dump(schema, sys.stdout, ensure_ascii=False, indent=2)
