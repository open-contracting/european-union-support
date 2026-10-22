# AGENTS.md

Internal tooling and source files for the [OCDS for eForms](https://standard.open-contracting.org/profiles/eforms/latest/en/) profile: a mapping from each field of the EU's eForms notices to OCDS.

## Layout

- `output/mapping/eforms/guidance.yaml`: the mapping, one entry per eForms field. This is where nearly all work happens.
- `output/mapping/eforms/mapping-tables/`: CSV mappings from eForms codes to OCDS codes, referenced by the guidance.
- `output/content/eforms/`: documentation pages; `operations.md` defines the common operations that guidance links to.
- `source/`: downloaded inputs (`fields.json` and `notice-types.json` from the eForms SDK, the regulation annex). Never edit by hand; `script/2019_download.fish TAG` replaces them.
- `codes-eforms.csv` (gitignored): the SDK's codelists, from `./manage.py codelists --ref TAG`.
- `manage.py`: all commands. Run with the project's virtual environment, e.g. `uv run ./manage.py --help`.
- `2019_regulation.md`: the process documentation, including the `guidance.yaml` data dictionary and style rules.

## guidance.yaml

Keys are either generated or manual, never both:

- **Generated** by `update-with-sdk` (from `fields.json`: `id` to `pattern`), `update-with-annex` (`Description`, `Business groups`) and `update-with-xpath` (`TED Xpath`). Don't hand-edit these: the next run reverts the edit. Fix the source or the command instead.
- **Manual**: `eForms guidance`, `eForms example`, `OCDS example`, `sdk`.
- **Reference**: `TED guidance` is the guidance from the earlier EU profile, for TED XML. Don't edit it.

When writing guidance, follow "Fill in the mapping file" and "Manual checks" in `2019_regulation.md`, and check open issues for the business term first. Reuse the wording of existing guidance for similar fields, rather than phrasing anew. The most common patterns are:

- A link to an operation in `operations.md`, like "[Get the lot for the ProcurementProjectLot](operations.md#...)", followed by "Map to its `.field`." or "Set its `.field` to 'value'."
- "Add a `Type` object to the `.array` array:", followed by indented steps.
- "This field maps to the same `Type` objects as created for [BT-xxx](<#BT-xxx>)."
- "Look up the code in the [authority table](...), and map its label to `.x` and its URI to `.y`."
- "Discard." with a sentence on how the value can be inferred from OCDS, if it can.

Then run `./manage.py lint output/mapping/eforms/guidance.yaml`, which validates the examples and normalizes formatting.

## OCDS extensions

When eForms data has no OCDS field or code, look for an existing extension before proposing a new field.

- The profile's extensions are listed in the eForms extension's [extension_versions.json](https://raw.githubusercontent.com/open-contracting-extensions/eforms/latest/docs/extension_versions.json). Using an extension that isn't listed means adding it to the profile.
- The Extension Explorer's [extensions.json](https://extensions.open-contracting.org/extensions.json) has every registered extension's metadata, schemas, codelists and readme, for every version. Search it, rather than guessing from extension names. Community extensions can be hosted outside GitHub, like itemAttributes on GitLab.
- To add a code to an extension's codelist (like `largeBids` in open-contracting-extensions/ocds_bid_extension#58), edit `codelists/*.csv` and the "Unreleased" changelog entry in its `README.md`, and open a pull request in the extension's repository.

## Conventions

- Mapping decisions are discussed in GitHub issues before guidance changes. Propose; don't decide alone. Draft issues and comments for the user to approve before posting.
- Commit messages: `feat: ...`, `fix: ...`, `chore: ...`, or a path prefix for guidance edits, like `output/mapping/eforms/guidance.yaml: Fix BT-22 fields`.
- Linting: `pre-commit` runs ruff (`select = ["ALL"]`) on Python files.

## Tasks with their own instructions

- eForms SDK upgrades: `.claude/skills/eforms-sdk-upgrade/SKILL.md`
