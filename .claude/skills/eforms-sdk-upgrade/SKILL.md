---
name: eforms-sdk-upgrade
description: Upgrade this repository to a new eForms SDK version (download sources, run the update-with-* commands, commit) and draft the GitHub issue that documents what changed for the OCDS mapping, in the style of past "eForms SDK x.y.z" issues. Use when asked to upgrade, bump or check a new eForms SDK release, or to document an SDK release's changes.
---

# eForms SDK upgrade

Upgrade one SDK version per step, commit it, then document the step in a GitHub issue. The goal of the issue is to tell the mapping analysts which changes need their attention, and why the rest don't.

The commands are documented in `2019_regulation.md` ("Upgrade SDK version"). This skill adds the order of operations, the checks between them, and how to triage and write up the result.

## 1. Plan the steps

```bash
python3 -c "import json; print(json.load(open('source/fields.json'))['sdkVersion'])"
gh release list -R OP-TED/eForms-SDK --exclude-pre-releases --limit 30
gh issue list --search 'eForms SDK in:title' --state all --limit 10
```

- Step through each **minor** version in order, using its **latest patch** (e.g. 1.13.0 → 1.13.3 → 1.14.2 → 1.15.1), so that each issue describes one minor version's changes.
- A patch-only step (1.13.0 → 1.13.3) is documented as a **comment** on that minor version's existing issue. A minor or major step gets a **new issue**.
- Skip pre-releases (`-alpha`, `-beta`) unless the user asks. They are useful for previewing an upcoming change, but don't commit them to `main`.
- Work on a branch, e.g. `sdk-1.15`. Each step is one commit, so a reviewer can follow the diff version by version.

Tell the user the plan (which steps, which become issues and which become comments) before running anything.

## 2. Check the baseline

The pipeline must reproduce the committed `guidance.yaml` before you change the version, or tooling drift will show up as fake SDK changes. Run step 3's commands **with the current version**, then `git diff --stat`.

- No diff: proceed.
- A diff: find the cause. Common causes: a dependency upgrade broke `manage.py` (fix it), or someone hand-edited a generated key like `Description` (the pipeline reverts it; accept the pipeline's value, since generated keys must match their source). Commit the fix separately (`fix: ...` or `chore: ...`) before upgrading.

## 3. Run one step

```bash
fish script/2019_download.fish TAG
# Redirect to a file. Piping to `head` kills the command before it writes guidance.yaml.
./manage.py update-with-sdk --verbose output/mapping/eforms/guidance.yaml > SCRATCH/sdk-verbose-TAG.txt
./manage.py update-with-annex output/mapping/eforms/guidance.yaml
./manage.py lint -a output/mapping/eforms/guidance.yaml
# For step 6. Slow: one request per codelist. Write to the scratchpad; codes-eforms.csv is gitignored.
./manage.py codelists --ref OLD_TAG > SCRATCH/codes-OLD_TAG.csv
./manage.py codelists --ref TAG > SCRATCH/codes-TAG.csv
```

Run `manage.py` with the project's virtual environment (`uv run ./manage.py`, or activate `.venv`).

Checks:

- `update-with-annex` should print only "N rows written". Anything else (e.g. "These rows were not included in the update: BT-67") means the SDK changed a `btId` or the annex changed. Find the cause. If a code fix is simple (like copying the annex row for suffixed `btId`s, as for BT-67(a) and BT-67(b)), propose it. Otherwise, the team's fallback is to fill in `Description` and `Business groups` manually; say so in the issue.
- `update-with-sdk --verbose` lists dropped fields. Yellow ones are forbidden on every supported notice type (`supported_notice_types` excludes X01 and X02). A field that moved to X01- or X02-only notices disappears from `guidance.yaml`, so it looks removed. Say so in the issue.
- If `source/CELEX_...xlsx` is 0 bytes, the annex URL in `script/2019_download.fish` is broken. Restore the file (`git checkout source/CELEX_32019R1780_EN_ANNEX_TABLE2_Extended.xlsx`) and tell the user.

## 4. Handle new properties

Run the summarizer against the last commit:

```bash
uv run python .claude/skills/eforms-sdk-upgrade/scripts/summarize.py HEAD
```

Its "fields.json properties" section lists properties that the SDK added. A new property lands in `guidance.yaml` as a key **after** the manual keys, which is a sign that it needs a decision.

Find each property's definition, and cite it in the issue:

1. The [field properties](https://docs.ted.europa.eu/eforms/latest/fields/index.html) page. Use `latest`: versioned URLs like `/eforms/1.15.0/` return 404. (In October 2026, it defined `numericRange` but not `dateFieldId`.)
2. The release notes (`gh release view TAG -R OP-TED/eForms-SDK`).
3. SDK issues and discussions: `gh search issues --repo OP-TED/eForms-SDK PROPERTY`, and https://github.com/OP-TED/eForms-SDK/discussions.
4. If undocumented, the values in `source/fields.json` (e.g. `dateFieldId` links a time field to its date field). Say in the issue that it's undocumented, and how you inferred its meaning.

Then:

- Irrelevant to mapping (validation, display or tooling metadata, like `numericRange`, `businessEntityId`): add it to the `drop` list in `update_with_sdk`, with a `# x.y.z` comment, like the existing entries.
- Possibly relevant: ask the user. If kept, add it to `column_order` in `get_column_order`, and to the data dictionary in `2019_regulation.md`.

Commit the `manage.py` change on its own (`feat: Drop the new numericRange property`), then re-run step 3.

## 5. Remove deleted fields, and commit

`update-with-sdk` keeps fields deleted from the SDK, with only their manual keys (`eForms guidance`, `eForms example`, `OCDS example`, `sdk`). The summarizer lists them, quoting any substantive guidance, so the issue preserves it.

- Delete them from `guidance.yaml`, **unless** the field was split or renamed (e.g. BT-541-Lot became BT-541-Lot-FixedNumber etc. in 1.8.0, OPT-999 became OPT-999-notice in 1.15.0) and the old guidance should be adapted for the new fields. In that case, leave it and say so in the issue.

Commit `source/` and `guidance.yaml` together: `feat: Upgrade to eForms SDK TAG`.

## 6. Triage

Generate the raw material, and read the release notes for every release in the step (including skipped patches):

```bash
uv run python .claude/skills/eforms-sdk-upgrade/scripts/summarize.py HEAD~1 HEAD \
    --codes SCRATCH/codes-OLD_TAG.csv SCRATCH/codes-TAG.csv
gh release view TAG -R OP-TED/eForms-SDK
```

The summarizer is mechanical. **You** decide the relevance of each change, by reading the field's `eForms guidance`, `eForms example` and `OCDS example` **at the step's commit** (`git show REF:output/mapping/eforms/guidance.yaml`, if later steps are already committed).

First, check that the step's commit is sound: the summarizer flags "annex data lost" if `update-with-annex` failed to merge a field. Report that as a tooling item, not a mapping change.

The summarizer sees only `fields.json` (and codelists, with `--codes`). Business rules and view templates appear only in the release notes, so scan them for changes that make guidance moot or newly needed: fields **hidden** or filled by a **preset** value, and codes added to or removed from a codelist that has a mapping table or that the guidance names. The summarizer's "Codelists" section lists the exact codes (flag: "used in mapping"); without `--codes`, check them by hand.

The release notes' "Addition of" items under notice types are usually existing fields allowed on more notice types, not new fields. The summarizer's "Notice types" section lists them, and the fields newly forbidden. They're relevant only if a field's guidance depends on the notice type, or if the notice type is unsupported (X01, X02). Otherwise, list them under "Not relevant", so readers of the release notes don't think we missed new fields. "Addition of" items under view templates only change how notices are displayed.

Re-check the issues that wait on an SDK change: `gh issue list --label blocked --state open`. Read each one's comments to find its blocker, which is often an OP-TED/eForms-SDK issue. Skip issues blocked on something else, like OCDS 1.2. For the rest, check whether the step's `fields.json` or release notes make the change, even if the SDK issue is still open (e.g. #121 waits for BT-157-LotsGroup or BT-271-LotsGroup to be removed). If one is unblocked, say so in the write-up.

Past decisions (see #188, #196, #204 and #215 for the discussions):

**Relevant** (needs a change to guidance, examples, extensions or code):

- New fields. These need guidance. Give each one's name and type. Group related fields (e.g. "Review", "Energy Efficiency Directive") and link the release note that explains them.
- Deleted fields with substantive guidance. Quote it, and say where it should go if a field replaces it.
- `xpathAbsolute` changes where the `eForms example` no longer matches (summarizer flag: "eForms example lacks"). Changes that only add or move a predicate, like `[cbc:ID/text()='CrossBorderLaw']`, usually need nothing; say so.
- Codelist renames that appear in an `eForms example`'s `listName` or in the guidance (flag: "mentions"). Note: `listName` is the codelist's `parentId` in `source/fields.json`, if it has one, else its `id`. A tailored codelist (e.g. `nuts-lvl3`, parent `nuts`) can be renamed without changing `listName`. #120 missed this.
- Removed codes that a mapping table or the guidance uses (flag: "used in mapping"). Added codes in a codelist that has a mapping table in `output/mapping/eforms/mapping-tables/` (the table needs a row).
- `type` changes, when the OCDS field's type differs (e.g. `number` → `integer` is fine if OCDS is already integer).
- `btId` changes, which can break `update-with-annex`.

**Maybe relevant** (an analyst should glance at each):

- Fields that became mandatory while their guidance is "Discard", "If true, ..." or "If not 'false', ...". Precedent: a mandatory indicator field changes guidance from "set X to true" to "map to X" (#204), unless OCDS can express "false" only by omission (e.g. a role); and a discarded field needs a sentence on how its value can be inferred from OCDS (#196, #204). "(conditional)" means mandatory only when an SDK rule's condition holds; the release notes say which.
- Fields that became optional, when they map to a required OCDS field.
- `repeatable` changes, when the guidance maps to a non-array OCDS field. The SDK marks the parent node repeatable instead of an only child; `update-with-sdk` corrects for this, so check the regulation annex before trusting it (#188).

**Not relevant** (list briefly, with counts, so readers know they were checked):

- `pattern`, `parentNodeId`, `name` wording, `Description` and `Business groups` (from the annex), notice types added to or removed from `mandatory` without a change to whether the field is ever mandatory, `mandatory` becoming conditional, new properties added to `drop`, and other business-rule, view-template, label and translation changes.

When unsure, put the change under "Maybe relevant" with your reasoning and a question for the analysts, rather than proposing guidance yourself. Writing new guidance is a separate task, done after the team discusses the issue.

## 7. Draft the issue or comment

Write the draft to a file in the scratchpad, show it to the user, and post only after they approve:

```bash
gh issue create --title "eForms SDK TAG" --body-file DRAFT
gh issue comment NUMBER --body-file DRAFT  # patch-only step
```

Structure, following #204, #215 and #227:

```markdown
https://github.com/OP-TED/eForms-SDK/releases/tag/TAG (and the other releases in the step, e.g. x.y.0 and x.y.1, noting which matter)

x.(y-1) was #NUMBER

Upgraded in COMMIT_SHA.

## Tooling

- [ ] Changes to `manage.py` that were made, or that are still needed (new `drop` entries, failed annex merges).

## Relevant

### New fields (N)

- [ ] BT-xxx-Lot Name (type)

### Deleted fields

- OPT-xxx-Lot (guidance was Discard)
- BT-yyy-Lot. The guidance was:

  ```yaml
  ...
  ```

### Changed XPaths

- BT-xxx-Lot: what changed. "Update eForms example" or "no change needed, because ..."

## Maybe relevant

### Now mandatory

- BT-xxx-Lot (CN): the guidance is Discard. Suggest: ...

## Not relevant

- `pattern` changed on N fields (`\d` → `[0-9]`)
- ...
```

- Omit empty sections; a quiet release may have only "Tooling" and "Not relevant". Use `- [ ]` checkboxes for items that need work, so the issue tracks progress.
- Be concrete: field IDs, before → after, and the reason something is or isn't relevant. Don't paste the summarizer output wholesale; long lists of IDs can go in a `<details>` block.
- For a patch-only comment, keep it to what changed and whether anything is relevant (often nothing is).
