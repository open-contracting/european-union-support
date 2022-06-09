#!/usr/bin/env python
import csv
import json
import os
import re
from pathlib import Path
from textwrap import dedent

import click
import requests
import numpy as np
import pandas as pd

basedir = Path(__file__).resolve().parent
sourcedir = basedir / 'source'
mappingdir = basedir / 'output' / 'mapping'
eformsdir = mappingdir / 'eforms'


def unique(series):
    """
    Return the unique values of a series.
    """
    series.dropna(inplace=True)

    # Write "null" not "[]".
    if series.empty:
        return None

    # Lists of lists are not supported by `Series.unique()` ("2015 guidance").
    if isinstance(series.iloc[0], np.ndarray):
        return sorted(set(item for array in series for item in array))

    return series.unique()


def check(actual, expected, noun):
    """
    Assert that ``actual`` equals ``expected``, with a templated error message.
    """
    assert actual == expected, f'expected {expected} {noun}, got {actual}'


def report_unmerged_rows(df, columns, series=None, unformatted=()):
    """
    If the data frame (or the ``series`` within it) is non-empty, print the data frame's ``columns``.
    """
    if series is not None:
        df = df[series]
    if not df.empty:
        # Why, pandas? https://stackoverflow.com/a/67202912/244258
        formatters = {
            col: f'{{:<{df[col].str.len().max()}s}}'.format
            for col in df.columns[df.dtypes == 'object'] if col not in unformatted
        }
        click.echo(f"{df[columns].to_string(index=False, formatters=formatters)}\nRows unmerged: {df.shape[0]}")


def write(filename, df, overwrite=None, explode=None, compare=None, how='left', **kwargs):
    """
    Read the data frame from the file (if it exists) and merge it with ``df`` according to ``how`` and ``kwargs``,
    overwriting only the ``overwrite`` columns.

    If ``explode`` is a list, explode the data frame before merging, then group the data frame by the "id" column
    after merging. (This option allows merging against a list.)

    If ``compare`` is a dict, print any rows in which the cells that match the dict's key and value don't match.
    """
    df_unmerged = pd.DataFrame()

    # Default to the data frame's columns.
    column_order = df.columns.format()

    if os.path.exists(filename):
        df_old = pd.read_json(filename, orient='records')

        # Maintain the column order.
        column_order = df_old.columns.format()
        for column in overwrite:
            if column not in column_order:
                column_order.append(column)

        # Pandas has no option to overwrite cells, so we drop first. Protect "id" from being overwritten.
        df_old.drop(columns=[column for column in overwrite if column != 'id'], errors='ignore', inplace=True)

        if explode:
            df_old = df_old.explode(explode)

        df_outer = df_old.merge(df, how='outer', indicator=True, **kwargs)
        # To return the unmerged rows.
        df_unmerged = df_outer[df_outer['_merge'] == 'right_only']

        if compare:
            for label, row in df_outer[df_outer['_merge'] == 'both'].iterrows():
                for a, b in compare.items():
                    actual, expected = row[a], row[b]
                    if actual != expected:
                        click.echo(f'{row["id"].ljust(35)}: {b} : {a} / {expected.ljust(50)} : {actual}')

        drop = [column for column in df.columns if column not in overwrite]
        # Merge all the columns, then drop the non-overwritten columns.
        df = df_old.merge(df, how=how, **kwargs).drop(columns=drop)

        if explode:
            df = df.groupby('id').agg({
                column: unique if column in explode or column in overwrite else 'first' for column in column_order
            })

    # Stop pandas from writing ints as floats.
    for column in ('maxLength', '2019 form', '2015 form'):
        if column in df.columns:
            df[column] = df[column].astype('Int64')

    # Initialize, fill in, and order the manually-edited columns.
    for column in ('2019 guidance', 'sdk', 'status', 'comments'):
        if column not in df.columns:
            df[column] = pd.Series(dtype='object')
        else:
            column_order.remove(column)
        df[column].fillna('', inplace=True)
        column_order.append(column)

    # Remove columns that do not assist the mapping process and that lengthen the JSON file.
    for column in ('forbidden', 'mandatory'):
        if column in df.columns:
            column_order.remove(column)

    df[column_order].to_json(filename, orient='records', indent=2)
    click.echo(f'{df.shape[0]} rows written')

    return df_unmerged


# https://github.com/pallets/click/issues/486
@click.group(context_settings={'max_content_width': 150})
def cli():
    pass


@cli.command()
@click.argument('filename', type=click.Path())
def update_with_sdk(filename):
    """
    Create or update FILE with fields metadata from the eForms SDK.
    """
    with (sourcedir / 'fields.json').open() as f:
        df = pd.DataFrame.from_dict(json.load(f)['fields'])

    write(filename, df, df.columns, how='outer', on='id', validate='1:1')


@cli.command()
@click.argument('filename', type=click.Path(exists=True))
def update_with_annex(filename):
    """
    Update FILE with details from the 2019 regulation's annex.
    """
    # A warning is issued, because the Excel file has an unsupported extension.
    df = pd.read_excel(sourcedir / 'CELEX_32019R1780_EN_ANNEX_TABLE2_Extended.xlsx', 'Annex')

    # 0:Level, 1:ID, 2:Name, 3:Data type, 4:Repeatable, 5:Description, 6-50:Legal Status, 51:Fields not included in...
    check(df.shape[1], 52, 'columns')

    # Remove extra header rows.
    check(df['ID'].isna().sum(), 3, 'extra header rows')
    df = df[df['ID'].notna()]

    # Ensure there are no duplicates.
    df.set_index('ID', verify_integrity=True)

    # Normalize whitespace (used in "Business groups").
    df['Name'] = df['Name'].str.strip()

    # Add "Business groups" column, to assist mapping by providing context.
    df['Business groups'] = pd.Series(dtype='object')

    line = []
    previous_level = 0
    for label, row in df.iterrows():
        current_level = len(row['Level'])

        # Adjust the size of this line of the "tree", then update the head.
        if current_level > previous_level:
            line.append((None, None))
        elif current_level < previous_level:
            line = line[:current_level]
        line[-1] = [row['ID'], row['Name']]

        df.at[label, 'Business groups'] = dict(line[:-1]) if len(line) > 1 else None

        previous_level = current_level

    # We can now remove all rows for business groups.
    df = df[~df['ID'].str.startswith('BG-')]

    # The fields metadata covers "Name", "Data type", "Repeatable" and "Legal Status" ("forbidden" and "mandatory").
    # "Business groups" replaces "Level". "Fields not included in the legal text" isn't informative.
    #
    # Adding `compare={'name': 'Name'}` shows that the names agree, and differ mainly due to field:bt being m:1.
    df = write(filename, df, ['Description', 'Business groups'], left_on='btId', right_on='ID', validate='m:1')

    report_unmerged_rows(df, ['ID', 'Name'], ~df['ID'].isin({
        # Removed indicators in favor of corresponding scalars.
        # https://docs.ted.europa.eu/eforms/0.6.0/schema/all-in-one.html#extensionsSection
        'BT-53',  # Options (BT-54 Options Description)
        # https://docs.ted.europa.eu/eforms/0.6.0/schema/all-in-one.html#toolNameSection
        'BT-724',  # Tool Atypical (BT-124 Tool Atypical URL)
        # https://docs.ted.europa.eu/eforms/0.6.0/schema/all-in-one.html#_footnotedef_21
        'BT-778',  # Framework Maximum Participants (BT-113 Framework Maximum Participants Number)

        # See OPT-155 and OPT-156.
        # https://docs.ted.europa.eu/eforms/0.6.0/schema/competition-results.html#lotResultComponentsTable
        'BT-715',
        'BT-725',
        'BT-716',

        # See Table 3.
        # https://docs.ted.europa.eu/eforms/0.6.0/schema/parties.html#mappingOrganizationBTsSchemaComponentsTable
        'BT-08',
        'BT-770',

        # See Table 4 (also includes BT-330 and BT-1375).
        # https://docs.ted.europa.eu/eforms/0.6.0/schema/identifiers.html#pointlessDueToDesignSection
        'BT-557',
        'BT-1371',
        'BT-1372',
        'BT-1373',
        'BT-1374',
        'BT-1376',
        'BT-1377',
        'BT-1378',
        'BT-1379',
        'BT-13710',
        'BT-13711',
        'BT-13712',
        'BT-13715',
        'BT-13717',
        'BT-13718',
        'BT-13719',
        'BT-13720',
        'BT-13721',
        'BT-13722',
    }))


@cli.command()
@click.argument('filename', type=click.Path(exists=True))
def update_with_xpath(filename):
    """
    Update FILE with XPaths from TED XML.
    """

    # See the "Legend" sheet for the data dictionary.
    with pd.ExcelFile(sourcedir / 'TED-XML-to-eForms-mapping-OP-public-20220404.xlsx') as xlsx:
        df = pd.read_excel(xlsx, 'tedxml_to_eforms_mapping.v0.4', na_values=['---', 'no match', 'no direct match'])

    for a, b, in (('Field ID', 'eForms BT ID'), ('eForms BT ID', 'Field ID')):
        actual = df[df['TED Xpath'].notna() & df[a].isna() & df[b].notna()]
        if not actual[b].empty:
            # The BTs seem to be mapped for other forms, so the omissions seem to be accidental and inconsequential.
            click.secho(f'Expected "{b}" to be N/A if "{a}" is N/A. Rows unmerged:', fg='yellow')
            click.echo(actual[['eForms BT ID', 'TED level', 'TED Xpath']].to_string(index=False))

    # We assume that the "Field ID" and "TED Xpath" are correct. Otherwise, we could check the eForms columns for
    # discrepancies: "eForms BT ID", "BT name", "Type", "Codelist", "Code", "eForms Xpath".
    #
    # "EC notes" (~100) and "OP comments" (~10) aren't informative. "Mapping ID" is an internal identifier.
    #
    # "TED level" and "TED element" can be added, but they might not add anything new.

    df = df.groupby('Field ID').agg({'TED Xpath': unique})
    write(filename, df, ['TED Xpath'], left_on='id', right_on='Field ID', validate='1:m')


@cli.command()
@click.argument('filename', type=click.Path(exists=True))
def update_with_ted_guidance(filename):
    """
    Update FILE with guidance for TED XML.
    """

    # Collect the guidance.
    dfs = []
    for path in sorted(mappingdir.glob('*.csv')):
        df = pd.read_csv(path)
        # Ignore rows without guidance (like defence forms), or for which the guidance is to discard.
        df = df[df['guidance'].notna()]
        # Prefix the XPath to match the spreadsheet used in `update-with-xpath`.
        df['xpath'] = f'TED_EXPORT/FORM_SECTION/{path.stem}' + df['xpath']
        # Add the form for more concise reporting.
        df['form'] = path.stem.replace('_2014', '')
        dfs.append(df)

    # ignore_index is required, as each data frame repeats indices.
    df = pd.concat(dfs, ignore_index=True).rename(columns={'guidance': '2015 guidance'}, errors='raise')
    # This drops "index" and "comment", which are of no assistance to mapping, and "label-key".
    df = df.groupby('xpath').agg({'2015 guidance': unique, 'form': 'first'})
    # We need to promote the "xpath" index to a column for it to be returned by `write`.
    df['index'] = df.index

    df = write(filename, df, ['2015 guidance'], explode=['TED Xpath'], left_on='TED Xpath', right_on='xpath')

    # Some TED elements cannot be converted to eForms.
    # https://github.com/OP-TED/ted-xml-data-converter/blob/main/ted-elements-not-convertible.md
    url = 'https://raw.githubusercontent.com/OP-TED/ted-xml-data-converter/main/ted-elements-not-convertible.md'
    elements = []
    for line in requests.get(url).text.splitlines():
        match = re.search(r'^\| ([A-Z_]+) \|', line)
        if match:
            elements.append(match.group(1))

    # Ignore unmerged rows whose guidance is to discard.
    df = df[~df['2015 guidance'].astype(str).str.startswith(("['Discard", '["Discard'))]
    # Reduce duplication in the unmerged rows.
    df['index'] = df['index'].str.replace(r'TED_EXPORT/FORM_SECTION/[^/]+', '', regex=True)
    df = df.groupby('index').agg({'form': unique})
    df['xpath'] = df.index

    report_unmerged_rows(df, ['form', 'xpath'], ~df['xpath'].str.endswith(tuple(elements)), unformatted=['form'])


@cli.command()
@click.argument('filename', type=click.Path(exists=True))
def statistics(filename):
    """
    Print statistics on the progress of the guidance for the 2019 regulation.
    """
    df = pd.read_json(filename, orient='records')

    total = df.shape[0]
    imported = df[df['status'] == 'imported from standard forms'].shape[0]
    done = df[df['status'].str.startswith('done')].shape[0]
    ready = imported + done
    no_issue_no_2019_guidance = df[(df['status'] == '') & (df['2019 guidance'] == '')].shape[0]
    no_2015_guidance = df[df['2015 guidance'].isna()].shape[0]

    df_issue = df[df['status'].str.startswith('issue')]
    issue = df_issue.shape[0]
    issue_no_guidance = df_issue[df_issue['2019 guidance'] == ''].shape[0]

    condition = df['mandatory'].isna()
    df_mandatory = df[condition]
    total_mandatory = df_mandatory.shape[0]
    done_mandatory = df_mandatory[df_mandatory['status'].str.startswith('done')].shape[0]
    issue_mandatory = df_mandatory[df_mandatory['status'].str.startswith('issue')].shape[0]
    df_optional = df[~condition]
    total_optional = df_optional.shape[0]
    done_optional = df_optional[df_optional['status'].str.startswith('done')].shape[0]
    issue_optional = df_optional[df_optional['status'].str.startswith('issue')].shape[0]

    click.echo(dedent(f"""\
    - Fields ready for review: {ready}/{total} ({ready / total:.1%})
        - Imported from 2015 guidance: {imported} ({imported / total:.1%})
        - Added or edited after import: {done} ({done / total:.1%})
        - Per legal status:
            - Mandatory: {done_mandatory}/{total_mandatory} ({done_mandatory / total_mandatory:.1%}), {issue_mandatory} with open issues ({issue_mandatory / total_mandatory:.1%})
            - Optional: {done_optional}/{total_optional} ({done_optional / total_optional:.1%}), {issue_optional} with open issues ({issue_optional / total_optional:.1%})
    - Fields with [open issues](https://github.com/open-contracting/european-union-support/labels/eforms): {issue} ({issue / total:.1%}), {issue_no_guidance} without guidance
    - Fields without issues and without 2019 guidance: {no_issue_no_2019_guidance} ({no_issue_no_2019_guidance / total:.1%})
    - Fields without 2015 guidance: {no_2015_guidance} ({no_2015_guidance / total:.1%})
    """))  # noqa: E501


@cli.command()
@click.argument('file', type=click.File())
def fields_without_extensions(file):
    """
    Print undefined fields in the guidance for TED XML.
    """
    subjects = {
        # Unambiguous
        'award': 'awards',
        'contract': 'contracts',
        'lot': 'tender/lots',
        'party': 'parties',
        'release': '',
        'statistic': 'bids/statistics',
        'charge': 'contracts/implementation/charges',

        # Ambiguous
        'amendment': {
            'CHANGES': 'tender/amendments',
            'MODIFICATIONS_CONTRACT': 'contracts/amendments',
        },
        'classification': {
            'CONTRACTING_BODY': 'parties/details/classifications',
            'PROCEDURE': 'tender/procurementMethodRationaleClassifications',
        },
        'criterion': {
            'LEFTI': 'tender/selectionCriteria/criteria',
            'OBJECT_CONTRACT': 'tender/lots/awardCriteria/criteria',
        },
        'item': {
            'MODIFICATIONS_CONTRACT': 'contracts/items',
            'OBJECT_CONTRACT': 'tender/items',
        },
        'object': {
            '/OBJECT_CONTRACT/OBJECT_DESCR/EU_PROGR_RELATED': 'planning/budget/finance',
        },
    }

    unknowns = {
        # Unambiguous
        '.additionalContactPoints': 'parties',
        '.awardCriteria': 'tender',
        '.awardID': 'contracts',
        '.countryCode': 'parties/address',
        '.details.classifications': 'parties',
        '.documentType': 'tender/documents',
        '.estimatedValue.amount': 'contracts/implementation/charges',
        '.financingParty.id': 'planning/budget/finance',
        '.financingParty.name': 'planning/budget/finance',
        '.identifier.id': 'parties',
        '.identifier.legalName': 'parties',
        '.identifier.scheme': 'parties',
        '.measure': 'bids/statistics',  # metrics extension not used
        '.minimum': 'tender/selectionCriteria/criteria',
        '.paidBy': 'contracts/implementation/charges',
        '.roles': 'parties',
        '.secondStage.maximumCandidates': 'tender/lots',
        '.secondStage.minimumCandidates': 'tender/lots',
        '.subcontracting.maximumPercentage': 'awards',
        '.suppliers': 'awards',  # contract suppliers extension not used

        # Ambiguous
        '.additionalClassifications': {
            'MODIFICATIONS_CONTRACT': 'contracts/items',
        },
        '.description': {
            # Root
            'LEFTI': 'tender/selectionCriteria/criteria',
            'PROCEDURE': 'tender/procurementMethodRationaleClassifications',
            # XPath
            '/CONTRACTING_BODY/CA_ACTIVITY': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_ACTIVITY/@VALUE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_ACTIVITY_OTHER': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_TYPE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_TYPE/@VALUE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_TYPE_OTHER': 'parties/details/classifications',
            '/CONTRACTING_BODY/CE_ACTIVITY': 'parties/details/classifications',
            '/CONTRACTING_BODY/CE_ACTIVITY/@VALUE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CE_ACTIVITY_OTHER': 'parties/details/classifications',
            '/OBJECT_CONTRACT/CATEGORY': 'tender/additionalClassifications',
            '/OBJECT_CONTRACT/CATEGORY/@CTYPE': 'tender/additionalClassifications',
            '/OBJECT_CONTRACT/OBJECT_DESCR/EU_PROGR_RELATED': 'planning/budget/finance',
        },
        '.id': {
            # Root
            'CHANGES': 'tender/amendments',
            'LEFTI': 'tender/documents',
            'PROCEDURE': 'tender/procurementMethodRationaleClassifications',
            # XPath
            '/AWARD_CONTRACT': 'awards',
            '/AWARD_CONTRACT/AWARDED_CONTRACT': 'contracts',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR': 'awards/suppliers',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/CONTRACTORS/CONTRACTOR/ADDRESS_PARTY': 'parties/shareholders',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED': 'bids/statistics',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_EMEANS': 'bids/statistics',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_NON_EU': 'bids/statistics',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_OTHER_EU': 'bids/statistics',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/TENDERS/NB_TENDERS_RECEIVED_SME': 'bids/statistics',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/VAL_PRICE_PAYMENT': 'contracts/implementation/charges',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/VAL_REVENUE': 'contracts/implementation/charges',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/HIGH': 'bids/statistics',
            '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/LOW': 'bids/statistics',
            '/CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY': 'parties',
            '/CONTRACTING_BODY/DOCUMENT_RESTRICTED': 'tender/participationFees',
            '/CONTRACTING_BODY/CA_ACTIVITY': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_ACTIVITY/@VALUE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_ACTIVITY_OTHER': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_TYPE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_TYPE/@VALUE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CA_TYPE_OTHER': 'parties/details/classifications',
            '/CONTRACTING_BODY/CE_ACTIVITY': 'parties/details/classifications',
            '/CONTRACTING_BODY/CE_ACTIVITY/@VALUE': 'parties/details/classifications',
            '/CONTRACTING_BODY/CE_ACTIVITY_OTHER': 'parties/details/classifications',
            '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR': 'awards/suppliers',  # noqa: E501
            '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_ADDITIONAL/CPV_CODE': 'contracts/items/additionalClassifications',  # noqa: E501
            '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE': 'contracts/items/additionalClassifications',  # noqa: E501
            '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE': 'contracts/items/additionalClassifications',  # noqa: E501
            '/MODIFICATIONS_CONTRACT/INFO_MODIFICATIONS': 'contracts/amendments',
            '/OBJECT_CONTRACT/CATEGORY': 'tender/additionalClassifications',
            '/OBJECT_CONTRACT/CATEGORY/@CTYPE': 'tender/additionalClassifications',
            '/OBJECT_CONTRACT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE': 'tender/items/additionalClassifications',
            '/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_CODE': 'tender/items/additionalClassifications',
            '/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE': 'tender/items/additionalClassifications',  # noqa: E501
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
            'RESULTS': 'awards/suppliers',
            # XPath
            '/CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY': 'buyer',
            '/PROCEDURE/PARTICIPANT_NAME': 'parties',
            '/PROCEDURE/MEMBER_NAME': 'tender/designContest/juryMembers',
        },
        '.newValue': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.newValue.classifications': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.newValue.date': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.newValue.text': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.oldValue': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.oldValue.classifications': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.oldValue.date': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.oldValue.text': {
            'CHANGES': 'tender/amendments/unstructuredChanges'
        },
        '.region': {
            '/OBJECT_CONTRACT/OBJECT_DESCR/NUTS': 'tender/items/deliveryAddresses',
            '/MODIFICATIONS_CONTRACT/DESCRIPTION_PROCUREMENT/NUTS': 'contracts/items/deliveryAddresses',
        },
        '.relatedLot': {
            'AWARD_CONTRACT': 'bids/statistics',
            'CHANGES': 'tender/amendments/unstructuredChanges',
            'RESULTS': 'bids/statistics',
        },
        '.relatedLots': {
            'AWARD_CONTRACT': 'awards',
            'OBJECT_CONTRACT': 'planning/budget/finance',
        },
        '.scheme': {
            'MODIFICATIONS_CONTRACT': 'contracts/items/additionalClassifications',
            # XPath
            '/CHANGES/CHANGE/NEW_VALUE/CPV_ADDITIONAL/CPV_CODE': 'tender/amendments/unstructuredChanges/newValue/classifications',  # noqa: E501
            '/CHANGES/CHANGE/NEW_VALUE/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE': 'tender/amendments/unstructuredChanges/newValue/classifications',  # noqa: E501
            '/CHANGES/CHANGE/NEW_VALUE/CPV_MAIN/CPV_CODE': 'tender/amendments/unstructuredChanges/newValue/classifications',  # noqa: E501
            '/CHANGES/CHANGE/NEW_VALUE/CPV_MAIN/CPV_SUPPLEMENTARY_CODE': 'tender/amendments/unstructuredChanges/newValue/classifications',  # noqa: E501
            '/CHANGES/CHANGE/OLD_VALUE/CPV_ADDITIONAL/CPV_CODE': 'tender/amendments/unstructuredChanges/oldValue/classifications',  # noqa: E501
            '/CHANGES/CHANGE/OLD_VALUE/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE': 'tender/amendments/unstructuredChanges/oldValue/classifications',  # noqa: E501
            '/CHANGES/CHANGE/OLD_VALUE/CPV_MAIN/CPV_CODE': 'tender/amendments/unstructuredChanges/oldValue/classifications',  # noqa: E501
            '/CHANGES/CHANGE/OLD_VALUE/CPV_MAIN/CPV_SUPPLEMENTARY_CODE': 'tender/amendments/unstructuredChanges/oldValue/classifications',  # noqa: E501
            '/OBJECT_CONTRACT/CPV_MAIN/CPV_SUPPLEMENTARY_CODE': 'tender/items/additionalClassifications',
            '/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_CODE': 'tender/items/additionalClassifications',
            '/OBJECT_CONTRACT/OBJECT_DESCR/CPV_ADDITIONAL/CPV_SUPPLEMENTARY_CODE': 'tender/items/additionalClassifications',  # noqa: E501
            '/OBJECT_CONTRACT/CATEGORY': 'tender/additionalClassifications',
        },
        '.shareholder.id': {
            'AWARD_CONTRACT': 'parties/shareholders',
        },
        '.shareholder.name': {
            'AWARD_CONTRACT': 'parties/shareholders',
        },
        '.status': {
            'AWARD_CONTRACT': 'contracts',
            'RESULTS': 'contracts',
        },
        '.title': {
            'AWARD_CONTRACT': 'contracts',
            'LEFTI': 'tender/targets',
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
        '.where': {
            'CHANGES': 'tender/amendments/unstructuredChanges',
        },
        '.where.label': {
            'CHANGES': 'tender/amendments/unstructuredChanges',
        },
        '.where.section': {
            'CHANGES': 'tender/amendments/unstructuredChanges',
        },
    }

    unhandled = set()
    paths = set()

    def report(path, row):
        value = (path, row.get('xpath'))
        if value not in unhandled:
            click.echo(f"unhandled: {path} ({row.get('xpath')}: {row['guidance']})", err=True)
        unhandled.add(value)

    for path in (mappingdir, mappingdir / 'shared'):
        for filename in path.glob('*.csv'):
            with filename.open() as f:
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
                                try:
                                    prefix = subjects[subject]
                                except KeyError as e:
                                    click.echo(f"KeyError: Add a {e} key to the `subjects` list")
                            elif path in unknowns:
                                try:
                                    prefix = unknowns[path]
                                except KeyError as e:
                                    click.echo(f"KeyError: Add a {e} key to the `unknowns` list")
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

    seen = [row['path'] for row in csv.DictReader(file)]
    for path in sorted(list(paths)):
        if path not in seen:
            click.echo(path)

    # Uncomment to print all the paths for a specific object.
    # for path in sorted(list(paths)):
    #     if '/items' in path:
    #         click.echo(path)


if __name__ == '__main__':
    cli()
