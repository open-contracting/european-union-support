"""Summarize the changes to guidance.yaml, fields.json and (optionally) codelists between two git refs, as Markdown."""

import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import click
import yaml

GUIDANCE = "output/mapping/eforms/guidance.yaml"
FIELDS = "source/fields.json"
MAPPING_TABLES = "output/mapping/eforms/mapping-tables"
MANUAL = ("eForms guidance", "eForms example", "OCDS example", "sdk")
# Keys whose changes are reported, in order of likely relevance to the mapping.
KEYS = (
    "btId",
    "xpathAbsolute",
    "type",
    "repeatable",
    "codeList",
    "schemeName",
    "idSchemes",
    "mandatory",
    "name",
    "parentNodeId",
    "pattern",
    "Description",
    "Business groups",
)
# Keys whose changes are grouped by (before, after), as these rarely affect the mapping.
GROUPED = ("pattern", "parentNodeId")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout  # noqa: S603 S607


def show(ref, path):
    """Return the file's contents at the ref, or in the working tree if the ref is empty."""
    if not ref:
        return Path(path).read_text()
    return git("show", f"{ref}:{path}")


def guidance(ref):
    # update-with-sdk keeps removed fields, without their generated keys.
    return {row["id"]: row for row in yaml.safe_load(show(ref, GUIDANCE)) if "xpathAbsolute" in row}


def field_keys(ref):
    keys = set()
    for field in json.loads(show(ref, FIELDS))["fields"]:
        keys.update(field)
    return keys


def forbidden(ref):
    """Return each field's unconditionally forbidden notice types. update-with-sdk drops this property."""
    out = {}
    for field in json.loads(show(ref, FIELDS))["fields"]:
        types = set()
        for constraint in (field.get("forbidden") or {}).get("constraints", []):
            if "condition" not in constraint:
                types |= set(constraint["noticeTypes"])
        out[field["id"]] = types
    return out


def codes(path):
    with path.open() as f:
        return {(row["codelist"], row["code"]) for row in csv.DictReader(f)}


def is_discard(row):
    return (row.get("eForms guidance") or "").startswith("Discard")


def describe(row, *, quote=False):
    """Describe the field's guidance, quoting its start if ``quote``."""
    text = row.get("eForms guidance")
    if not text:
        return "no guidance"
    if is_discard(row):
        return "guidance is Discard"
    if quote:
        first = text.strip().splitlines()[0].lstrip("- ")
        return f'guidance: "{first[:80]}{"..." if len(first) > 80 else ""}"'
    return "has guidance"


def last_step(xpath):
    """Return the last element name in the XPath, without predicates or namespace prefix."""
    step = re.sub(r"\[[^\]]*\]", "", xpath).rstrip("/").rsplit("/", 1)[-1]
    return step.split(":", 1)[-1].lstrip("@")


def flags(key, old, new, row):
    """Return heuristic flags for a changed key."""
    example = row.get("eForms example") or ""
    text = (row.get("eForms guidance") or "") + example
    out = []
    if key == "xpathAbsolute" and example and last_step(new) not in example:
        out.append(f"eForms example lacks `{last_step(new)}`")
    if key == "codeList" and isinstance(old, str) and old in text:
        out.append(f"guidance or example mentions `{old}`")
    if key == "repeatable" and new and row.get("eForms guidance") and not is_discard(row):
        out.append("now repeatable; check guidance maps to an array")
    if key == "btId":
        out.append("check update-with-annex merged this field")
    if key in {"Description", "Business groups"} and old and not new:
        out.append("annex data lost: update-with-annex didn't merge this field")
    return out


def shorten(before, after):
    """Remove the common leading steps of two XPaths."""
    if not before or not after:
        return before, after
    a, b = before.split("/"), after.split("/")
    n = 0
    while n < min(len(a), len(b)) - 1 and a[n] == b[n]:
        n += 1
    prefix = "…/" if n else ""
    return prefix + "/".join(a[n:]), prefix + "/".join(b[n:])


def notice_types(value):
    """Return the notice types in a ``mandatory`` value, suffixing conditional ones with "?"."""
    out = set()
    for constraint in (value or "").split(" & "):
        conditional = constraint.endswith(" (conditional)")
        for t in constraint.removesuffix(" (conditional)").split():
            out.add(t + "?" if conditional else t)
    return out


def fmt(value, limit=120):
    if value is None:
        return "∅"
    if isinstance(value, (dict, list)):
        return f"`{json.dumps(value, ensure_ascii=False)}`"
    text = str(value).replace("\n", " ")
    if limit and len(text) > limit:
        text = text[: limit - 3] + "..."
    return f"`{text}`"


def echo_new(old, new):
    click.echo("## New fields\n")
    for i in sorted(set(new) - set(old)):
        row = new[i]
        mandatory = f", mandatory: {row['mandatory']}" if row.get("mandatory") else ""
        click.echo(f"- [ ] {i} {row.get('name', '')} ({row.get('type', '')}{mandatory})")


def echo_removed(old, new):
    click.echo("\n## Removed fields\n")
    click.echo("update-with-sdk leaves these in guidance.yaml with only their manual keys. Remove them manually.\n")
    for i in sorted(set(old) - set(new)):
        row = old[i]
        click.echo(f"- {i} {row.get('name', '')} ({describe(row)})")
        if row.get("eForms guidance") and not is_discard(row):
            text = yaml.safe_dump({k: row[k] for k in MANUAL if row.get(k)}, allow_unicode=True, sort_keys=False)
            click.echo("\n  ```yaml\n" + "".join(f"  {line}\n" for line in text.splitlines()) + "  ```\n")


def echo_mandatory(changes):
    click.echo("Now mandatory:\n")
    for i, before, _, row in changes:
        if not before:
            note = " **guidance is Discard**" if is_discard(row) else ""
            click.echo(f"- {i} ({describe(row, quote=True)}): {row['mandatory']}{note}")
    click.echo("\nNow optional:\n")
    for i, _, after, row in changes:
        if not after:
            click.echo(f"- {i} ({describe(row, quote=True)})")

    groups = defaultdict(list)
    conditional = []
    for i, before, after, _ in changes:
        if not before or not after:
            continue
        a, b = notice_types(before), notice_types(after)
        bare_a, bare_b = {t.rstrip("?") for t in a}, {t.rstrip("?") for t in b}
        delta = [*(f"+{t}" for t in sorted(bare_b - bare_a)), *(f"-{t}" for t in sorted(bare_a - bare_b))]
        shared = bare_a & bare_b
        if no_longer := sorted(t for t in shared if t in b and f"{t}?" in a):
            delta.append(f"no longer conditional on {' '.join(no_longer)}")
        if delta:
            groups["; ".join(delta)].append(i)
        elif any(t in a and f"{t}?" in b for t in shared):
            conditional.append(i)
        else:
            groups["reordered"].append(i)
    click.echo("\nNotice types changed:\n")
    for delta, ids in sorted(groups.items(), key=lambda item: -len(item[1])):
        click.echo(f"- {delta} ({len(ids)}): {', '.join(ids)}")
    if conditional:
        click.echo(f"- Only became conditional on some notice types ({len(conditional)}): {', '.join(conditional)}")


def echo_changed(old, new):
    changes = defaultdict(list)
    for i in sorted(set(old) & set(new)):
        for key in KEYS:
            if old[i].get(key) != new[i].get(key):
                changes[key].append((i, old[i].get(key), new[i].get(key), new[i]))

    click.echo("\n## Changed fields\n")
    for key in KEYS:
        if not changes[key]:
            continue
        click.echo(f"### {key} ({len(changes[key])})\n")
        if key == "mandatory":
            echo_mandatory(changes[key])
        elif key in GROUPED:
            groups = defaultdict(list)
            for i, before, after, _ in changes[key]:
                groups[(fmt(before), fmt(after))].append(i)
            for (before, after), ids in groups.items():
                click.echo(f"- {before} → {after}: {', '.join(ids)}")
        else:
            for i, before, after, row in changes[key]:
                notes = flags(key, before, after, row)
                note = f" **{'; '.join(notes)}**" if notes else ""
                limit = 120
                if key == "xpathAbsolute":
                    before, after = shorten(before, after)
                    limit = 0
                click.echo(f"- {i} ({describe(row)}): {fmt(before, limit)} → {fmt(after, limit)}{note}")
        click.echo()


def echo_properties(base, head, old, new):
    old_keys, new_keys = field_keys(base), field_keys(head)
    old_columns = {k for row in old.values() for k in row}
    new_columns = sorted({k for row in new.values() for k in row} - old_columns)
    click.echo("## fields.json properties\n")
    click.echo(f"- Added: {', '.join(sorted(new_keys - old_keys)) or 'none'}")
    click.echo(f"- Removed: {', '.join(sorted(old_keys - new_keys)) or 'none'}")
    click.echo(f"- New keys in guidance.yaml (add to `drop` in update-with-sdk): {', '.join(new_columns) or 'none'}")


def echo_codes(head, old_path, new_path):
    if not old_path or not new_path:
        click.echo("\n## Codelists\n\nNot compared (pass --codes OLD.csv NEW.csv).")
        return
    old_codes, new_codes = codes(old_path), codes(new_path)
    if old_codes == new_codes:
        click.echo("\n## Codelists\n\nUnchanged.")
        return

    mapped = show(head, GUIDANCE) + "".join(show(head, path) for path in git("ls-files", MAPPING_TABLES).split())
    click.echo("\n## Codelists\n")
    for label, diff in (("Added", new_codes - old_codes), ("Removed", old_codes - new_codes)):
        by_list = defaultdict(list)
        for codelist, code in sorted(diff):
            by_list[codelist.removesuffix(".gc")].append(code)
        # Tailored codelists (e.g. legal-basis_legal-basis-1) repeat their parent's changes.
        by_values = defaultdict(list)
        for codelist, values in by_list.items():
            by_values[tuple(values)].append(codelist)
        for values, codelists in by_values.items():
            # Match codes as quoted strings, XML text or CSV cells, not as words in prose. Skip codes that a tailored
            # codelist removed, but that its parent (e.g. legal-basis for legal-basis_legal-basis-1) still has.
            used = (
                [
                    v
                    for v in values
                    if re.search(rf"""(^|['"`>,]){re.escape(v)}($|['"`<,])""", mapped, re.MULTILINE)
                    and not all((f"{c.split('_')[0]}.gc", v) in new_codes for c in codelists)
                ]
                if label == "Removed"
                else []
            )
            note = f" **used in mapping: {', '.join(used)}**" if used else ""
            more = " ..." if len(values) > 15 else ""
            names = ", ".join(f"`{c}`" for c in codelists)
            click.echo(f"- {label} in {names}: {', '.join(values[:15])}{more}{note}")


def echo_notice_types(base, head, new):
    """Report fields allowed on, or forbidden from, more notice types (in release notes, "Addition of" fields)."""
    old_forbidden, new_forbidden = forbidden(base), forbidden(head)
    groups = {"Newly allowed on": defaultdict(list), "Newly forbidden on": defaultdict(list)}
    for i in sorted(set(new) & set(old_forbidden) & set(new_forbidden)):
        if allowed := old_forbidden[i] - new_forbidden[i]:
            groups["Newly allowed on"][" ".join(sorted(allowed))].append(i)
        if forbade := new_forbidden[i] - old_forbidden[i]:
            groups["Newly forbidden on"][" ".join(sorted(forbade))].append(i)
    click.echo("## Notice types\n")
    for label, by_types in groups.items():
        for types, ids in sorted(by_types.items(), key=lambda item: -len(item[1])):
            click.echo(f"- {label} {types}: {', '.join(f'{i} ({describe(new[i])})' for i in ids)}")
    click.echo()


@click.command(help=__doc__)
@click.argument("base")
@click.argument("head", default="")
@click.option(
    "--codes",
    nargs=2,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The output of `manage.py codelists --ref` for the old and new SDK tags",
)
def main(base, head, codes):
    """Compare BASE (e.g. HEAD~1) to HEAD (default: the working tree)."""
    old, new = guidance(base), guidance(head)
    echo_new(old, new)
    echo_removed(old, new)
    echo_changed(old, new)
    echo_notice_types(base, head, new)
    echo_properties(base, head, old, new)
    echo_codes(head, *(codes or (None, None)))


if __name__ == "__main__":
    main()
