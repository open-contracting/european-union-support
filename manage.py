#!/usr/bin/env python
import csv
import filecmp
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from copy import deepcopy
from io import StringIO
from pathlib import Path
from textwrap import dedent, indent
from urllib.parse import urlsplit

import click
import json_merge_patch
import lxml.etree
import lxml.html
import mdformat
import numpy as np
import pandas as pd
import requests
import yaml
from jsonpointer import set_pointer
from jsonschema import FormatChecker
from jsonschema.validators import Draft4Validator as validator
from ocdsextensionregistry import ProfileBuilder

# from ocdskit.mapping_sheet import mapping_sheet

basedir = Path(__file__).resolve().parent
sourcedir = basedir / "source"
outputdir = basedir / "output"
mappingdir = outputdir / "mapping"
eformsdir = mappingdir / "eforms"
contentdir = outputdir / "content" / "eforms"

# From https://github.com/OP-TED/eForms-SDK/tree/main/examples
# See https://docs.ted.europa.eu/eforms/latest/schema/schemas.html
xmlhead = (
    '<ContractNotice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
    'xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" '
    'xmlns="urn:oasis:names:specification:ubl:schema:xsd:ContractNotice-2" '
    'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" '
    'xmlns:efac="http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1" '
    'xmlns:efext="http://data.europa.eu/p27/eforms-ubl-extensions/1" '
    'xmlns:efbc="http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
)
xmltail = "</ContractNotice>"


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def na_representer(dumper, data):
    return dumper.represent_data(None)


def ndarray_representer(dumper, data):
    return dumper.represent_data(data.tolist())


def float_representer(dumper, data):
    if np.isnan(data):
        return dumper.represent_data(None)
    return dumper.represent_float(data)


def str_representer(dumper, data):
    # Use the literal style on multiline strings to reduce quoting, instead of the single-quoted style (default).
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|" if "\n" in data else None)


Dumper.add_representer(pd._libs.missing.NAType, na_representer)
Dumper.add_representer(np.ndarray, ndarray_representer)
Dumper.add_representer(float, float_representer)
Dumper.add_representer(str, str_representer)


def get(url):
    """
    GET a URL and return the response.
    """
    response = requests.get(url)
    response.raise_for_status()
    return response


def get_html(url):
    """
    GET a URL and return the parsed HTML content.
    """
    return lxml.html.fromstring(get(url).content)


def unique(series):
    """
    Return the unique values of a series.
    """
    series.dropna(inplace=True)

    # Write "null" not "[]".
    if series.empty:
        return None

    # Lists of lists are not supported by `Series.unique()` ("TED guidance").
    if isinstance(series.iloc[0], np.ndarray):
        return sorted({item for array in series for item in array})

    return series.unique()


def check(actual, expected, noun):
    """
    Assert that ``actual`` equals ``expected``, with a templated error message.
    """
    assert actual == expected, f"expected {expected} {noun}, got {actual}"


def get_column_order(df, drop=()):
    # Pandas uses the order of appearance, within rows and *across* rows. Since we remove null values from the output,
    # the order of appearance across rows can differ from the order in a given row. A hardcoded list is needed to have
    # a consistent order.
    column_order = [
        "id",
        "parentNodeId",
        "name",
        "btId",
        "xpathAbsolute",
        "type",
        "schemeName",
        "idSchemes",
        "repeatable",
        "mandatory",
        "codeList",
        "pattern",
    ]
    for column in column_order:
        if column not in df.columns:
            column_order.remove(column)
    for column in df.columns.format():
        if column not in column_order:
            column_order.append(column)
    for column in drop:
        if column in column_order:
            column_order.remove(column)
    return column_order


def write_yaml_file(filename, data):
    with open(filename, "w") as f:
        # Make it easier to see indentation. Avoid line wrapping. sort_keys is True by default.
        yaml.dump(data, f, Dumper=Dumper, indent=4, width=1000, sort_keys=False)


def report_unmerged_rows(df, columns, series=None, unformatted=()):
    """
    If the data frame (or the ``series`` within it) is non-empty, print the data frame's ``columns``.
    """
    if series is not None:
        df = df[series]
    if not df.empty:
        # "Why, pandas?" https://stackoverflow.com/a/67202912/244258
        formatters = {
            col: f"{{:<{df[col].str.len().max()}s}}".format
            for col in df.columns[df.dtypes == "object"]
            if col not in unformatted
        }
        click.echo("These rows were not included in the update:")
        click.echo(f"{df[columns].to_string(index=False, formatters=formatters)}\nRows unmerged: {df.shape[0]}")


# From standard-maintenance-scripts/tests/test_readme.py
def set_additional_properties_and_remove_pattern_properties(data, additional_properties):
    if isinstance(data, list):
        for item in data:
            set_additional_properties_and_remove_pattern_properties(item, additional_properties)
    elif isinstance(data, dict):
        if "properties" in data:
            data["additionalProperties"] = additional_properties
        if "patternProperties" in data:
            del data["patternProperties"]
        for value in data.values():
            set_additional_properties_and_remove_pattern_properties(value, additional_properties)


def write(filename, df, overwrite=None, explode=None, compare=None, how="left", drop=(), **kwargs):
    """
    Read the data frame from the file (if it exists) and merge it with ``df`` according to ``how`` and ``kwargs``,
    overwriting only the ``overwrite`` columns.

    If ``explode`` is a list, explode the data frame before merging, then group the data frame by the "id" column
    after merging. (This option allows merging against a list.)

    If ``compare`` is a dict, print any rows in which the cells that match the dict's key and value don't match.
    """
    df_unmerged = pd.DataFrame()

    # Default to the data frame's columns.
    column_order = get_column_order(df, drop)

    if os.path.exists(filename):
        with open(filename) as f:
            df_old = pd.DataFrame.from_records(yaml.safe_load(f))

        # Maintain the column order.
        column_order = get_column_order(df_old, drop)
        for column in overwrite:
            if column not in column_order and column not in drop:
                column_order.append(column)

        # Pandas has no option to overwrite cells, so we drop first. Protect "id" from being overwritten.
        df_old.drop(columns=[column for column in overwrite if column != "id"], errors="ignore", inplace=True)

        if explode:
            df_old = df_old.explode(explode)

        df_outer = df_old.merge(df, how="outer", indicator=True, **kwargs)
        # To return the unmerged rows.
        df_unmerged = df_outer[df_outer["_merge"] == "right_only"]

        if compare:
            for label, row in df_outer[df_outer["_merge"] == "both"].iterrows():
                for a, b in compare.items():
                    actual, expected = row[a], row[b]
                    if actual != expected:
                        click.echo(f'{row["id"].ljust(35)}: {b} : {a} / {expected.ljust(50)} : {actual}')

        untouched = [column for column in df.columns if column not in overwrite]
        # Merge all the columns, then drop the non-overwritten columns.
        df = df_old.merge(df, how=how, **kwargs).drop(columns=untouched)

        if drop:
            df.drop(columns=drop, errors="ignore", inplace=True)

        if explode:
            df = df.groupby("id").agg(
                {column: unique if column in explode or column in overwrite else "first" for column in column_order}
            )

    # Stop pandas from writing ints as floats.
    for column in ("maxLength",):
        if column in df.columns:
            df[column] = df[column].astype("Int64")

    # Initialize, fill in, and order the manually-edited columns.
    for column in ("eForms guidance", "eForms example", "OCDS example", "sdk"):
        if column not in df.columns:
            df[column] = pd.Series(dtype="object")
        else:
            column_order.remove(column)
        df[column].fillna("", inplace=True)
        column_order.append(column)

    write_yaml_file(filename, [row.dropna().to_dict() for label, row in df[column_order].iterrows()])
    click.echo(f"{df.shape[0]} rows written")

    return df_unmerged


# https://github.com/pallets/click/issues/486
@click.group(context_settings={"max_content_width": 150})
def cli():
    pass


@cli.command()
@click.argument("filename", type=click.Path(dir_okay=False))
@click.option("-v", "--verbose", is_flag=True, help="Print verbose output")
def update_with_sdk(filename, verbose):
    """
    Create or update FILE with fields metadata from the eForms SDK.
    """
    with (sourcedir / "fields.json").open() as f:
        df = pd.DataFrame.from_dict(json.load(f)["fields"])

    labels = {}
    supported_notice_types = {str(i) for i in range(1, 41)} | {"CEI", "T01", "T02"}
    expected = {"value": False, "severity": "ERROR", "constraints": [{"value": True, "severity": "ERROR"}]}
    for label, row in df.iterrows():
        forbidden = row["forbidden"]
        if forbidden is np.nan:
            continue
        # Abbreviate the constraints (there is sometimes another constraint on X02, etc.).
        forbidden["constraints"] = forbidden["constraints"][:1]
        # If a field's forbidden types are a superset of all supported types, drop it.
        if (
            set(forbidden["constraints"][0].pop("noticeTypes")) >= supported_notice_types
            and "condition" not in forbidden["constraints"][0]
        ):
            # Ensure the forbidden property's structure is as expected.
            assert forbidden == expected, f"{row['id']} {forbidden} !=\n{expected}"
            labels[label] = row["id"]

    df.drop(index=labels, inplace=True)

    if verbose:
        click.echo(f"{df.shape[0]} kept, {len(labels)} dropped")
        click.echo("\n".join(sorted(f"- {label}" for label in labels.values())))

    # Remove or abbreviate columns that do not assist the mapping process and that lengthen the JSON file. See README.
    drop = [
        "xpathRelative",
        "presetValue",
        "legalType",
        "maxLength",
        "idScheme",
        "forbidden",
        "assert",
        "inChangeNotice",
        "privacy",
        "xsdSequenceOrder",
    ]
    df["mandatory"] = df["mandatory"].notna()
    # Simplify these columns if `severity` is the only other top-level key.
    for column in ("repeatable", "pattern"):
        df[column] = [cell["value"] if isinstance(cell, dict) and len(cell) == 2 else cell for cell in df[column]]
    # Simplify `codelist` as above, and if `type` and `parentId` (optional) are the only other second-level keys.
    df["codeList"] = [
        cell["value"]["id"] if isinstance(cell, dict) and len(cell) == 2 and 2 <= len(cell["value"]) <= 3 else cell
        for cell in df["codeList"]
    ]

    write(filename, df, df.columns, how="outer", drop=drop, on="id", validate="1:1")


@cli.command()
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
def update_with_annex(filename):
    """
    Update FILE with details from the 2019 regulation's annex.
    \f

    Add the columns:

    - Description
    - Business groups
    """
    # A warning is issued, because the Excel file has an unsupported extension.
    df = pd.read_excel(sourcedir / "CELEX_32019R1780_EN_ANNEX_TABLE2_Extended.xlsx", "Annex")

    # 0:Level, 1:ID, 2:Name, 3:Data type, 4:Repeatable, 5:Description, 6-50:Legal Status, 51:Fields not included in...
    check(df.shape[1], 52, "columns")

    # Remove extra header rows.
    check(df["ID"].isna().sum(), 3, "extra header rows")
    df = df[df["ID"].notna()]
    # BG-714 now identifies "CVD Information" in addition to "Review".
    if df.at[295, "ID"] == "BG-714":
        df.at[295, "ID"] = "BG-7140"

    # Ensure there are no duplicates.
    df.set_index("ID", verify_integrity=True)

    # Normalize whitespace (used in "Business groups").
    df["Name"] = df["Name"].str.strip()

    # Normalize whitespace.
    df["Description"] = df["Description"].str.replace(" ", " ", regex=False)  # non-breaking space

    # Add "Business groups" column, to assist mapping by providing context.
    df["Business groups"] = pd.Series(dtype="object")

    line = []
    previous_level = 0
    for label, row in df.iterrows():
        current_level = len(row["Level"])

        # Adjust the size of this line of the "tree", then update the head.
        if current_level > previous_level:
            line.append((None, None))
        elif current_level < previous_level:
            line = line[:current_level]
        line[-1] = [row["ID"], row["Name"]]

        df.at[label, "Business groups"] = dict(line[:-1]) if len(line) > 1 else None

        previous_level = current_level

    # We can now remove all rows for business groups.
    df = df[~df["ID"].str.startswith("BG-")]

    # The fields metadata covers "Name", "Data type", "Repeatable" and "Legal Status" ("forbidden" and "mandatory").
    # "Business groups" replaces "Level". "Fields not included in the legal text" isn't informative.
    #
    # Adding `compare={'name': 'Name'}` shows that the names agree, and differ mainly due to field:bt being m:1.
    df = write(filename, df, ["Description", "Business groups"], left_on="btId", right_on="ID", validate="m:1")

    report_unmerged_rows(
        df,
        ["ID", "Name"],
        ~df["ID"].isin(
            {
                # Removed indicators in favor of corresponding scalars.
                # https://docs.ted.europa.eu/eforms/latest/schema/procedure-lot-part-information.html#extensionsSection
                "BT-53",  # Options (BT-54 Options Description)
                # https://docs.ted.europa.eu/eforms/latest/schema/procedure-lot-part-information.html#toolNameSection
                "BT-724",  # Tool Atypical (BT-124 Tool Atypical URL)
                # https://docs.ted.europa.eu/eforms/latest/schema/procedure-lot-part-information.html#_footnotedef_9
                "BT-778",  # Framework Maximum Participants (BT-113 Framework Maximum Participants Number)
                # See OPT-155 and OPT-156.
                # https://docs.ted.europa.eu/eforms/latest/schema/competition-results.html#lotResultComponentsTable
                "BT-715",
                "BT-725",
                "BT-716",
                # See Table 3.
                # https://docs.ted.europa.eu/eforms/latest/schema/parties.html#mappingOrganizationBTsSchemaComponentsTable
                "BT-08",
                "BT-770",
                # See Table 4 (also includes BT-330 and BT-1375).
                # https://docs.ted.europa.eu/eforms/latest/schema/identifiers.html#pointlessDueToDesignSection
                "BT-557",
                "BT-1371",
                "BT-1372",
                "BT-1373",
                "BT-1374",
                "BT-1376",
                "BT-1377",
                "BT-1378",
                "BT-1379",
                "BT-13710",
                "BT-13711",
                "BT-13712",
                "BT-13715",
                "BT-13717",
                "BT-13718",
                "BT-13719",
                "BT-13720",
                "BT-13721",
                "BT-13722",
            }
        ),
    )


@cli.command()
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
def update_with_xpath(filename):
    """
    Update FILE with XPaths from TED XML.
    \f

    Add the columns:

    - TED Xpath
    """

    # See the "Legend" sheet for the data dictionary.
    with pd.ExcelFile(sourcedir / "TED-XML-to-eForms-mapping-OP-public-20220404.xlsx") as xlsx:
        df = pd.read_excel(xlsx, "tedxml_to_eforms_mapping.v0.4", na_values=["---", "no match", "no direct match"])

    for a, b in (("Field ID", "eForms BT ID"), ("eForms BT ID", "Field ID")):
        actual = df[df["TED Xpath"].notna() & df[a].isna() & df[b].notna()]
        if not actual[b].empty:
            # The BTs seem to be mapped for other forms, so the omissions seem to be accidental and inconsequential.
            click.secho(f'Expected "{b}" to be N/A if "{a}" is N/A. Rows unmerged:', fg="yellow")
            click.echo(actual[["eForms BT ID", "TED level", "TED Xpath"]].to_string(index=False))

    # We assume that the "Field ID" and "TED Xpath" are correct. Otherwise, we could check the eForms columns for
    # discrepancies: "eForms BT ID", "BT name", "Type", "Codelist", "Code", "eForms Xpath".
    #
    # "EC notes" (~100) and "OP comments" (~10) aren't informative. "Mapping ID" is an internal identifier.
    #
    # "TED level" and "TED element" can be added, but they might not add anything new.

    df = df.groupby("Field ID").agg({"TED Xpath": unique})
    write(filename, df, ["TED Xpath"], left_on="id", right_on="Field ID", validate="1:m")

    # We don't report_unmerged_rows(), because rows are merged on field ID.


@cli.command()
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
def update_with_ted_guidance(filename):
    """
    Update FILE with guidance for TED XML.
    \f

    Add the columns:

    - TED guidance
    """

    # Collect the guidance.
    dfs = []
    for path in sorted(mappingdir.glob("*.csv")):
        df = pd.read_csv(path)
        # Ignore rows without guidance (like defence forms), or for which the guidance is to discard.
        df = df[df["guidance"].notna()]
        # Prefix the XPath to match the spreadsheet used in `update-with-xpath`.
        df["xpath"] = f"TED_EXPORT/FORM_SECTION/{path.stem}" + df["xpath"]
        # Add the form for more concise reporting.
        df["form"] = path.stem.replace("_2014", "")
        dfs.append(df)

    # ignore_index is required, as each data frame repeats indices.
    df = pd.concat(dfs, ignore_index=True).rename(columns={"guidance": "TED guidance"}, errors="raise")
    # This drops "index" and "comment", which are of no assistance to mapping, and "label-key".
    df = df.groupby("xpath").agg({"TED guidance": unique, "form": "first"})
    # We need to promote the "xpath" index to a column for it to be returned by `write`.
    df["index"] = df.index

    df = write(filename, df, ["TED guidance"], explode=["TED Xpath"], left_on="TED Xpath", right_on="xpath")

    # Ignore unmerged rows whose guidance is to discard.
    df = df[~df["TED guidance"].astype(str).str.startswith(("['Discard", '["Discard'))]
    # Reduce duplication in the unmerged rows.
    df["index"] = df["index"].str.replace(r"TED_EXPORT/FORM_SECTION/[^/]+", "", regex=True)
    df = df.groupby("index").agg({"form": unique})
    df["xpath"] = df.index

    # Some TED elements cannot be converted to eForms.
    # https://github.com/OP-TED/ted-xml-data-converter/blob/main/ted-elements-not-convertible.md
    url = "https://raw.githubusercontent.com/OP-TED/ted-xml-data-converter/main/ted-elements-not-convertible.md"
    elements = []
    for line in get(url).text.splitlines():
        if match := re.search(r"^\| ([A-Z_]+) \|", line):
            elements.append(match.group(1))

    report_unmerged_rows(df, ["form", "xpath"], ~df["xpath"].str.endswith(tuple(elements)), unformatted=["form"])


@cli.command()
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
@click.option("-a", "--additional-properties", is_flag=True, help="Allow additional properties")
def lint(filename, additional_properties):
    """
    Lint FILE (validate and format XML, JSON and Markdown, report unrecognized OCDS fields, update eForms SDK URLs).
    """

    # Similar to tests/fixtures/release_minimal.json in ocdskit.
    minimal_release = {
        "ocid": "ocds-213czf-1",
        "id": "1",
        "date": "2001-02-03T04:05:06Z",
        "tag": ["planning"],
        "initiationType": "tender",
        "tender": {
            "id": "1e86a664-ae3c-41eb-8529-0242ac130003",
        },
    }
    set_missing_ids = {
        ("tender", "items"): ("id",),
        ("tender", "lots"): ("id",),
        ("tender", "lotGroups"): ("id",),
        ("awards",): ("id",),
        ("contracts",): ("id", "awardID"),
    }

    with open(filename) as f:
        fields = yaml.safe_load(f)

    url = "https://raw.githubusercontent.com/open-contracting-extensions/eforms/latest/docs/extension_versions.json"
    schema = ProfileBuilder("1__1__5", get(url).json()).patched_release_schema(extension_field="extension")

    # The idea was to compare the additional fields to known prefixes, but this mostly results in the lots extension.
    # I am leaving this code here for now, in case we need to do something smarter.
    # fieldnames, rows = mapping_sheet(schema, extension_field="extension", inherit_extension=False)
    # prefixes = {row["path"]: row.get("extension") for row in rows}

    # Remove `patternProperties` to clarify output.
    set_additional_properties_and_remove_pattern_properties(schema, additional_properties)
    # Remove required fields.
    for definition in ("Bid", "Statistic", "Document", "Finance", "ParticipationFee", "Person"):
        set_pointer(schema, f"/definitions/{definition}/required", [])

    format_checker = FormatChecker()

    if os.path.isfile("codes.txt"):
        with open("codes.txt") as f:
            known_codes = set(f.read().splitlines())
    else:
        known_codes = set()
        url = "https://standard.open-contracting.org/profiles/eforms/latest/en/_static/patched/codelists/"
        document = get_html(url)
        document.make_links_absolute(url)
        for url in document.xpath('//@href[contains(., ".csv")]'):
            reader = csv.DictReader(StringIO(get(url).text))
            for row in reader:
                known_codes.add(row["Code"])

        with open("codes.txt", "w") as f:
            f.write("\n".join(sorted(known_codes)))

    if os.path.isfile("codes-eforms.csv"):
        with open("codes-eforms.csv") as f:
            known_eforms_codes = {row["code"] for row in csv.DictReader(f)}
    else:
        known_eforms_codes = set()

    sdk_documents = {}

    unreviewed = 0

    http_errors = set()
    anchor_errors = set()
    single_quoted = defaultdict(list)
    double_quoted = defaultdict(list)
    additional_fields = defaultdict(list)
    for field in fields:
        identifier = field["id"]

        # Update and check SDK URLs.
        if field["sdk"]:
            parsed = urlsplit(field["sdk"])
            fragment = parsed.fragment
            base_url = parsed._replace(fragment="").geturl()
            try:
                if base_url not in sdk_documents:
                    sdk_documents[base_url] = get_html(base_url)
                if not fragment:
                    if not field["id"].endswith("-Contract"):
                        anchor_errors.add(f"{identifier}: no anchor")
                elif not sdk_documents[base_url].xpath(f'//@id="{fragment}"'):
                    anchor_errors.add(f"{identifier}: anchor not found: {fragment}")
            except requests.exceptions.HTTPError:
                http_errors.add(base_url)

        # Format Markdown.
        field["eForms guidance"] = mdformat.text(field["eForms guidance"]).rstrip()
        unreviewed += field["eForms guidance"].startswith("(UNREVIEWED)")

        for match in re.finditer(r"'(\S+)'", field["eForms guidance"]):
            single_quoted[match.group(1)].append([field["id"], field["name"]])

        for match in re.finditer(r'"(\S+)"', re.sub(r"`[^`]+`", "", field["eForms guidance"])):
            double_quoted[match.group(1)].append([field["id"], field["name"]])

        # Format XML.
        eforms_example = field["eForms example"]
        if eforms_example and eforms_example != "N/A":
            try:
                element = lxml.etree.fromstring(f"{xmlhead}{eforms_example}{xmltail}")
                field["eForms example"] = lxml.etree.tostring(element).decode()[len(xmlhead) : -len(xmltail)]

                # Note: The XML snippets are too short to validate against the eForms schema.
            except lxml.etree.XMLSyntaxError as e:
                click.echo(f"{identifier}: XML is invalid: {e}: {eforms_example}")

        # Format and validate JSON.
        ocds_example = field["OCDS example"]
        if ocds_example and ocds_example != "N/A":
            try:
                data = json.loads(ocds_example)
                field["OCDS example"] = json.dumps(data, separators=(",", ":"))

                release = deepcopy(minimal_release)
                json_merge_patch.merge(release, data)

                for parents, keys in set_missing_ids.items():
                    obj = release
                    for parent in parents:
                        if parent in obj:
                            obj = obj[parent]
                        else:
                            break
                    else:
                        for key in keys:
                            if key not in obj[0]:
                                obj[0][key] = "1"

                for e in validator(schema, format_checker=format_checker).iter_errors(release):
                    if e.validator == "additionalProperties":
                        e.absolute_schema_path[-1] = "properties"
                        e.absolute_schema_path.append("")
                        for match in re.findall(r"'(\S+)'", e.message):
                            e.absolute_schema_path[-1] = match
                            additional_fields[
                                "/".join(e.absolute_schema_path)
                                .replace("items/properties/", "")
                                .replace("properties/", "")
                            ].append([field["id"], field["name"]])
                    else:
                        click.echo(f"{identifier}: OCDS is invalid: {e.message} ({'/'.join(e.absolute_schema_path)})")
            except json.decoder.JSONDecodeError as e:
                click.echo(f"{identifier}: JSON is invalid: {e}: {ocds_example}")

    unknown_codes = {code: v for code, v in single_quoted.items() if code not in known_codes}
    if unknown_codes:
        click.echo("\nOCDS codes (tokens in single quotes) that do not appear in any OCDS codelist:")
        click.echo("code,id,title")
        for code, occurrences in sorted(unknown_codes.items(), key=lambda item: item[1]):
            click.echo(f"{code}{''.join(f',{identifier},{title}' for identifier, title in occurrences)}")

    unknown_eforms_codes = {code: v for code, v in double_quoted.items() if code not in known_eforms_codes}
    if unknown_eforms_codes:
        click.echo("\neForms codes (tokens in double quotes) that do not appear in any eForms codelist:")
        click.echo("code,id,title")
        for code, occurrences in sorted(unknown_eforms_codes.items(), key=lambda item: item[1]):
            click.echo(f"{code}{''.join(f',{identifier},{title}' for identifier, title in occurrences)}")

    if unreviewed:
        click.echo(f"\n{unreviewed} unreviewed eForms guidance")

    for title, errors in (
        ("HTTP errors", http_errors),
        ("Anchor errors", anchor_errors),
    ):
        if errors:
            click.echo(f"\n{title} ({len(errors)}):")
            click.echo("\n".join(sorted(errors)))

    if additional_fields:
        click.echo(f"\nAdditional fields ({len(additional_fields)}):")
        click.echo("field,id,title")
        for field, occurrences in sorted(additional_fields.items(), key=lambda item: item[1]):
            click.echo(f"{field}{''.join(f',{identifier},{title}' for identifier, title in occurrences)}")

    write_yaml_file(filename, fields)


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
def build(directory):
    def copy_if_changed(src, dst):
        if not (dst / src.name).exists() or not filecmp.cmp(src, dst / src.name):
            shutil.copy(src, dst)

    def write_if_changed(path, new):
        old = ""
        new = dedent(new)
        if path.exists():
            with path.open() as f:
                old = f.read()
        if old != new:
            with path.open("w") as f:
                f.write(new)

    def replace_if_changed(path, replacement):
        if path.exists():
            with path.open() as f:
                content = f.read()
            if match := re.search(r"<!-- [^\n]*-->\n\n(.+)", content, re.DOTALL):
                write_if_changed(path, content.replace(match.group(1), dedent(replacement)))
            else:
                click.echo(f"{path} does not contain <!-- ... -->")
        else:
            click.echo(f"{path} does not exist")

    docsdir = Path(directory) / "docs"
    codelistsdir = docsdir / "codelists"

    # Copy the content pages.
    for file in contentdir.iterdir():
        copy_if_changed(file, docsdir)

    # Create the codelist mapping pages.
    stems = []
    for file in (eformsdir / "mapping-tables").iterdir():
        stem = file.stem
        stems.append(stem)

        copy_if_changed(file, codelistsdir)

        write_if_changed(
            codelistsdir / f"{stem}.md",
            f"""\
            # {stem}

            ```{{csv-table}}
            :header-rows: 1
            :file: {stem}.csv
            ```
            """,
        )

    stems = "\n".join(sorted(stems))
    replace_if_changed(
        codelistsdir / "index.md",
        f"```{{toctree}}\n:maxdepth: 1\n\n{stems}\n```\n",
    )

    # Create the main mapping page.
    with open(eformsdir / "guidance.yaml") as f:
        fields = yaml.safe_load(f)

    rows = []
    for field in fields:
        description = field.get("Description", "")
        if description:
            description = f"<p><i>{field['btId']}:</i> {description}</p>"

        sdk = field["sdk"]
        if sdk:
            sdk = f'<a class="reference external" href="{sdk}"></a>'

        required = ""
        if field["mandatory"]:
            required = "<b>*</b>"

        eforms_example = field["eForms example"]
        if eforms_example and eforms_example != "N/A":
            element = lxml.etree.fromstring(f"{xmlhead}{eforms_example}{xmltail}")
            lxml.etree.indent(element, space="  ")
            data = dedent(lxml.etree.tostring(element).decode()[len(xmlhead) + 1 : -len(xmltail) - 1])
            eforms_example = f"```xml\n{data}\n```"
        else:
            eforms_example = ""

        ocds_example = field["OCDS example"]
        if ocds_example and ocds_example != "N/A":
            data = json.dumps(json.loads(ocds_example), ensure_ascii=False, indent=2).replace("Infinity", "1e9999")
            ocds_example = f"```json\n{data}\n```"
        else:
            ocds_example = ""

        # Replace within-page anchors with HTML anchors, to avoid "reference target not found".
        guidance = re.sub(
            r"\[([^\]]+)\]\((?:<(#[^>]+)>|(#[^)]+))\)",
            lambda match: f'<a href="{match.group(2) or match.group(3)}">{match.group(1)}</a>',
            field["eForms guidance"],
        )

        rows.append(
            f"""\
              <tr id="{field["id"]}">
                <td class="field break-all">
                    <p><b>{field["id"]}</b> {required} {sdk}<br>{field["name"]}</p>{description}
                    <code class="docutils literal notranslate"><span class="pre">{field["xpathAbsolute"]}</span></code>
                </td>
                <td class="mapping">

{indent(guidance, '        ')}

{indent(eforms_example, '        ')}

{indent(ocds_example, '        ')}

        </td>
              </tr>"""
        )

    rows = "\n".join(rows)
    replace_if_changed(
        docsdir / "mapping.md",
        f"""\
        <div id="mappings" class="wy-table-responsive">
          <p>
            <label for="mappings-search">
              Search the table by eForms field, business term, XML element, OCDS field, etc.:
            </label>
            <input id="mappings-search" class="search" placeholder="Search">
          </p>
          <table class="docutils">
            <colgroup>
              <col width="30%">
              <col width="70%">
            </colgroup>
            <thead>
              <tr>
                <th>eForms field</th>
                <th>OCDS mapping</th>
              </tr>
            </thead>
            <tbody class="list">
{rows}
            </tbody>
          </table>
        </div>

        <script src="//cdnjs.cloudflare.com/ajax/libs/list.js/1.5.0/list.min.js"></script>
        <script>new List('mappings', {{valueNames: ['field', 'mapping']}})</script>
        """,
    )


@cli.command()
def business_groups():
    """
    Print information about eForms Business Groups (BGs).
    """
    # A warning is issued, because the Excel file has an unsupported extension.
    df = pd.read_excel(sourcedir / "CELEX_32019R1780_EN_ANNEX_TABLE2_Extended.xlsx", "Annex")

    # Remove extra header rows.
    df = df[df["ID"].notna()]

    # Normalize whitespace.
    df["Name"] = df["Name"].str.strip()
    df["Description"] = df["Description"].str.strip()

    # Keep only rows for business groups.
    df = df[df["ID"].str.startswith("BG-")]

    df[["Level", "ID", "Name", "Repeatable", "Description"]].to_csv(eformsdir / "business-groups.csv", index=False)


@cli.command()
def codelists():
    """
    Print information about eForms codelists.
    """
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["codelist", "code"])

    for file in get("https://api.github.com/repos/OP-TED/eForms-SDK/contents/codelists").json():
        if not file["name"].endswith(".gc"):
            continue

        xml = lxml.etree.fromstring(get(file["download_url"]).content)
        writer.writerows([file["name"], code] for code in xml.xpath('//Value[@ColumnRef="code"]/SimpleValue/text()'))


@cli.command()
@click.argument("file", type=click.File())
def statistics(file):
    """
    Print statistics on the progress of the guidance for the 2019 regulation.
    """
    df = pd.DataFrame.from_records(yaml.safe_load(file))
    key = "eForms guidance"

    total = df.shape[0]
    done = df[df[key] != ""].shape[0]
    reviewed = done - df[df[key].str.startswith("(UNREVIEWED)")].shape[0]
    no_ted_guidance = df[df["TED guidance"].isna()].shape[0]

    condition = df["mandatory"]
    df_m = df[condition]
    total_m = df_m.shape[0]
    done_m = df_m[df_m[key] != ""].shape[0]
    reviewed_m = done_m - df_m[df_m[key].str.startswith("(UNREVIEWED)")].shape[0]
    df_o = df[~condition]
    total_o = df_o.shape[0]
    done_o = df_o[df_o[key] != ""].shape[0]
    reviewed_o = done_o - df_o[df_o[key].str.startswith("(UNREVIEWED)")].shape[0]

    click.echo(
        dedent(
            f"""\
            reviewed/done/total (%reviewed %done)

            - Fields mapped: {reviewed}/{done}/{total} ({reviewed / total:.1%} {done / total:.1%})
                - Mandatory: {reviewed_m}/{done_m}/{total_m} ({reviewed_m / total_m:.1%} {done_m / total_m:.1%})
                - Optional: {reviewed_o}/{done_o}/{total_o} ({reviewed_o / total_o:.1%} {done_o / total_o:.1%})
            - Fields without TED guidance: {no_ted_guidance} ({no_ted_guidance / total:.1%})"""
        )
    )


@cli.command()
@click.argument("file", type=click.File())
@click.option("--contains", help="Print fields containing this text")
def fields_without_extensions(file, contains):
    """
    Print fields that appear in the TED XML guidance but not in the FILE mapping sheet.
    """
    subjects = {
        # Unambiguous
        "award": "awards",
        "contract": "contracts",
        "lot": "tender/lots",
        "party": "parties",
        "release": "",
        "statistic": "bids/statistics",
        "charge": "contracts/implementation/charges",
        #
        # Ambiguous
        "amendment": {
            "CHANGES": "tender/amendments",
            "MODIFICATIONS_CONTRACT": "contracts/amendments",
        },
        "classification": {
            "CONTRACTING_BODY": "parties/details/classifications",
            "PROCEDURE": "tender/procurementMethodRationaleClassifications",
        },
        "criterion": {
            "LEFTI": "tender/selectionCriteria/criteria",
            "OBJECT_CONTRACT": "tender/lots/awardCriteria/criteria",
        },
        "item": {
            "MODIFICATIONS_CONTRACT": "contracts/items",
            "OBJECT_CONTRACT": "tender/items",
        },
        "object": {
            "/OBJECT_CONTRACT/OBJECT_DESCR/EU_PROGR_RELATED": "planning/budget/finance",
        },
    }

    unknowns = {
        # Unambiguous
        ".additionalContactPoints": "parties",
        ".awardCriteria": "tender",
        ".awardID": "contracts",
        ".countryCode": "parties/address",
        ".details.classifications": "parties",
        ".documentType": "tender/documents",
        ".estimatedValue.amount": "contracts/implementation/charges",
        ".financingParty.id": "planning/budget/finance",
        ".financingParty.name": "planning/budget/finance",
        ".identifier.id": "parties",
        ".identifier.legalName": "parties",
        ".identifier.scheme": "parties",
        ".measure": "bids/statistics",  # metrics extension not used
        ".minimum": "tender/selectionCriteria/criteria",
        ".paidBy": "contracts/implementation/charges",
        ".roles": "parties",
        ".secondStage.maximumCandidates": "tender/lots",
        ".secondStage.minimumCandidates": "tender/lots",
        ".subcontracting.maximumPercentage": "awards",
        ".suppliers": "awards",  # contract suppliers extension not used
        #
        # Ambiguous
        ".additionalClassifications": {
            "MODIFICATIONS_CONTRACT": "contracts/items",
        },
        ".description": {
            # Root
            "LEFTI": "tender/selectionCriteria/criteria",
            "PROCEDURE": "tender/procurementMethodRationaleClassifications",
            # XPath
            "/CONTRACTING_BODY/CA_ACTIVITY": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_ACTIVITY/@VALUE": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_ACTIVITY_OTHER": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_TYPE": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_TYPE/@VALUE": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_TYPE_OTHER": "parties/details/classifications",
            "/CONTRACTING_BODY/CE_ACTIVITY": "parties/details/classifications",
            "/CONTRACTING_BODY/CE_ACTIVITY/@VALUE": "parties/details/classifications",
            "/CONTRACTING_BODY/CE_ACTIVITY_OTHER": "parties/details/classifications",
            "/OBJECT_CONTRACT/CATEGORY": "tender/additionalClassifications",
            "/OBJECT_CONTRACT/CATEGORY/@CTYPE": "tender/additionalClassifications",
            "/OBJECT_CONTRACT/OBJECT_DESCR/EU_PROGR_RELATED": "planning/budget/finance",
        },
        ".id": {
            # Root
            "CHANGES": "tender/amendments",
            "LEFTI": "tender/documents",
            "PROCEDURE": "tender/procurementMethodRationaleClassifications",
            # XPath
            "/AWARD_CONTRACT": "awards",
            "/AWARD_CONTRACT/AWARDED_CONTRACT": "contracts",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR": "awards/suppliers",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/CONTRACTORS/CONTRACTOR/ADDRESS_PARTY": "parties/shareholders",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED": "bids/statistics",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_EMEANS": "bids/statistics",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_NON_EU": "bids/statistics",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_OTHER_EU": "bids/statistics",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_SME": "bids/statistics",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/VAL_PRICE_PAYMENT": "contracts/implementation/charges",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/VAL_REVENUE": "contracts/implementation/charges",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/HIGH": "bids/statistics",
            "/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/LOW": "bids/statistics",
            "/CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY": "parties",
            "/CONTRACTING_BODY/DOCUMENT_RESTRICTED": "tender/participationFees",
            "/CONTRACTING_BODY/CA_ACTIVITY": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_ACTIVITY/@VALUE": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_ACTIVITY_OTHER": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_TYPE": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_TYPE/@VALUE": "parties/details/classifications",
            "/CONTRACTING_BODY/CA_TYPE_OTHER": "parties/details/classifications",
            "/CONTRACTING_BODY/CE_ACTIVITY": "parties/details/classifications",
            "/CONTRACTING_BODY/CE_ACTIVITY/@VALUE": "parties/details/classifications",
            "/CONTRACTING_BODY/CE_ACTIVITY_OTHER": "parties/details/classifications",
            "/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR": "awards/suppliers",  # noqa: E501
            "/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_ADDITIONAL/CPV_CODE": "contracts/items/additionalClassifications",  # noqa: E501
            "/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE": "contracts/items/additionalClassifications",  # noqa: E501
            "/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE": "contracts/items/additionalClassifications",  # noqa: E501
            "/MODIFICATIONS_CONTRACT/INFO_MODIFICATIONS": "contracts/amendments",
            "/OBJECT_CONTRACT/CATEGORY": "tender/additionalClassifications",
            "/OBJECT_CONTRACT/CATEGORY/@CTYPE": "tender/additionalClassifications",
            "/OBJECT_CONTRACT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE": "tender/items/additionalClassifications",
            "/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_CODE": "tender/items/additionalClassifications",
            "/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE": "tender/items/additionalClassifications",  # noqa: E501
            "/OBJECT_CONTRACT/OBJECT_DESCR/EU_PROGR_RELATED": "planning/budget/finance",
            "/OBJECT_CONTRACT/VAL_RANGE_TOTAL/HIGH": "bids/statistics",
            "/OBJECT_CONTRACT/VAL_RANGE_TOTAL/LOW": "bids/statistics",
            "/RESULTS/AWARDED_PRIZE": "contracts",
            "/RESULTS/AWARDED_PRIZE/PARTICIPANTS/NB_PARTICIPANTS": "bids/statistics",
            "/RESULTS/AWARDED_PRIZE/PARTICIPANTS/NB_PARTICIPANTS_OTHER_EU": "bids/statistics",
            "/RESULTS/AWARDED_PRIZE/PARTICIPANTS/NB_PARTICIPANTS_SME": "bids/statistics",
            "/RESULTS/AWARDED_PRIZE/WINNERS/WINNER/ADDRESS_WINNER": "awards/suppliers",
        },
        ".items": {
            "MODIFICATIONS_CONTRACT": "contracts",
        },
        ".name": {
            # Root
            "AWARD_CONTRACT": "awards/suppliers",
            "MODIFICATIONS_CONTRACT": "awards/suppliers",
            "OBJECT_CONTRACT": "parties",
            "RESULTS": "awards/suppliers",
            # XPath
            "/CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY": "buyer",
            "/PROCEDURE/PARTICIPANT_NAME": "parties",
            "/PROCEDURE/MEMBER_NAME": "tender/designContest/juryMembers",
        },
        ".newValue": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".newValue.classifications": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".newValue.date": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".newValue.text": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".oldValue": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".oldValue.classifications": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".oldValue.date": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".oldValue.text": {"CHANGES": "tender/amendments/unstructuredChanges"},
        ".region": {
            "/OBJECT_CONTRACT/OBJECT_DESCR/NUTS": "tender/items/deliveryAddresses",
            "/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/NUTS": "contracts/items/deliveryAddresses",
        },
        ".relatedLot": {
            "AWARD_CONTRACT": "bids/statistics",
            "CHANGES": "tender/amendments/unstructuredChanges",
            "RESULTS": "bids/statistics",
        },
        ".relatedLots": {
            "AWARD_CONTRACT": "awards",
            "OBJECT_CONTRACT": "planning/budget/finance",
        },
        ".scheme": {
            "MODIFICATIONS_CONTRACT": "contracts/items/additionalClassifications",
            # XPath
            "/CHANGES/CHANGE/NEW_VALUE/CPV_ADDITIONAL/CPV_CODE": "tender/amendments/unstructuredChanges/newValue/classifications",  # noqa: E501
            "/CHANGES/CHANGE/NEW_VALUE/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE": "tender/amendments/unstructuredChanges/newValue/classifications",  # noqa: E501
            "/CHANGES/CHANGE/NEW_VALUE/CPV_MAIN/CPV_CODE": "tender/amendments/unstructuredChanges/newValue/classifications",  # noqa: E501
            "/CHANGES/CHANGE/NEW_VALUE/CPV_MAIN/CPV_SUPPLEMENTARY_CODE": "tender/amendments/unstructuredChanges/newValue/classifications",  # noqa: E501
            "/CHANGES/CHANGE/OLD_VALUE/CPV_ADDITIONAL/CPV_CODE": "tender/amendments/unstructuredChanges/oldValue/classifications",  # noqa: E501
            "/CHANGES/CHANGE/OLD_VALUE/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE": "tender/amendments/unstructuredChanges/oldValue/classifications",  # noqa: E501
            "/CHANGES/CHANGE/OLD_VALUE/CPV_MAIN/CPV_CODE": "tender/amendments/unstructuredChanges/oldValue/classifications",  # noqa: E501
            "/CHANGES/CHANGE/OLD_VALUE/CPV_MAIN/CPV_SUPPLEMENTARY_CODE": "tender/amendments/unstructuredChanges/oldValue/classifications",  # noqa: E501
            "/OBJECT_CONTRACT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE": "tender/items/additionalClassifications",
            "/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_CODE": "tender/items/additionalClassifications",
            "/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE": "tender/items/additionalClassifications",  # noqa: E501
            "/OBJECT_CONTRACT/CATEGORY": "tender/additionalClassifications",
        },
        ".shareholder.id": {
            "AWARD_CONTRACT": "parties/shareholders",
        },
        ".shareholder.name": {
            "AWARD_CONTRACT": "parties/shareholders",
        },
        ".status": {
            "AWARD_CONTRACT": "contracts",
            "RESULTS": "contracts",
        },
        ".title": {
            "AWARD_CONTRACT": "contracts",
            "LEFTI": "tender/targets",
        },
        ".type": {
            # Root
            "CONTRACTING_BODY": "tender/participationFees",
            "LEFTI": "tender.selectionCriteria.criteria",
            "OBJECT_CONTRACT": "tender/lots/awardCriteria/criteria",
        },
        ".value": {
            "AWARD_CONTRACT": "bids/statistics",
            "OBJECT_CONTRACT": "bids/statistics",
            "RESULTS": "bids/statistics",
        },
        ".where": {
            "CHANGES": "tender/amendments/unstructuredChanges",
        },
        ".where.label": {
            "CHANGES": "tender/amendments/unstructuredChanges",
        },
        ".where.section": {
            "CHANGES": "tender/amendments/unstructuredChanges",
        },
    }

    unhandled = set()
    paths = set()

    def report(path, row):
        value = (path, row.get("xpath"))
        if value not in unhandled:
            click.echo(f"unhandled: {path} ({row.get('xpath')}: {row['guidance']})", err=True)
        unhandled.add(value)

    for path in (mappingdir, mappingdir / "shared"):
        for filename in path.glob("*.csv"):
            with filename.open() as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("guidance"):
                        for match in re.finditer(r"(?:([a-z]+)'s )?\[?`([^`]+)`", row["guidance"]):
                            path = match.group(2)
                            if path in ("true", "false", "value"):  # JSON boolean, exceptional case
                                continue
                            if re.search(r"^[A-Z][a-z][A-Za-z]+$", path):  # JSON Schema definition
                                continue
                            if re.search(r"^(/[A-Z_]+)+$", path):  # XPath
                                continue
                            if re.search(r"^[A-Z_]+$", path):  # XML element
                                continue

                            subject = match.group(1)

                            prefix = ""
                            if subject:
                                try:
                                    prefix = subjects[subject]
                                except KeyError as e:
                                    click.echo(f"KeyError: Add a {e} key to the `subjects` list")
                            elif path in unknowns:
                                try:
                                    prefix = unknowns[path]
                                except KeyError as e:
                                    click.echo(f"KeyError: Add a {e} key to the `unknowns` list")
                            elif path[0] == ".":
                                report(path, row)
                                continue

                            if isinstance(prefix, dict):
                                xpath = row.get("xpath", "/")
                                root = xpath.split("/", 2)[1]
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
                            paths.add(path.replace(".", "/"))

    seen = [row["path"] for row in csv.DictReader(file)]
    for path in sorted(paths):
        if path not in seen:
            click.echo(path)

    if contains:
        click.echo(f"Contains '{contains}':")
        for path in sorted(paths):
            if contains in path:
                click.echo(path)


if __name__ == "__main__":
    cli()
