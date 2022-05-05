#!/usr/bin/env python
import csv
import json
import os
import re
from pathlib import Path
from textwrap import dedent

import click
import pandas as pd

basedir = Path(__file__).resolve().parent
sourcedir = basedir / 'source'
mappingdir = basedir / 'output' / 'mapping'
eformsdir = mappingdir / 'eforms'


def check(actual, expected, noun):
    assert actual == expected, f'expected {expected} {noun}, got {actual}'
    return actual


def report(df, columns, series):
    df = df[series]
    if not df.empty:
        click.echo(f'Rows unmerged: {df.shape[0]}\n{df[columns].to_string(index=False)}')


def write(filename, df, overwrite=None, compare=None, how='left', **kwargs):
    df_unmerged = pd.DataFrame()

    if os.path.exists(filename):
        df_old = pd.read_json(filename, orient='records')
        # Pandas has no option to overwrite cells, so we drop first.
        df_old.drop(columns=overwrite, errors='ignore', inplace=True)

        df_outer = df_old.merge(df, how='outer', indicator=True, **kwargs)
        # Return the unmerged rows.
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

    # Initialize the manually-edited columns.
    for column in ('guidance', 'status', 'comments'):
        if column not in df.columns:
            df[column] = pd.Series(dtype='string')
            df[column].fillna('', inplace=True)

    # Stop pandas from writing ints as floats.
    for column in ('maxLength', '2019 form', '2015 form'):
        if column in df.columns:
            df[column] = df[column].astype('Int64')

    df.to_json(filename, orient='records', indent=2)
    return df_unmerged


# https://github.com/pallets/click/issues/486
@click.group(context_settings={'max_content_width': 150})
def cli():
    pass


@cli.command()
@click.argument('filename', type=click.Path())
def update_with_sdk(filename):
    """
    Update FILE with fields metadata from the eForms SDK.
    """
    with (sourcedir / 'fields.json').open() as f:
        df = pd.DataFrame.from_dict(json.load(f)['fields'])

    overwrite = [column for column in df.columns if column != 'id']
    write(filename, df, overwrite, how='outer', on='id', validate='1:1')


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

    # The fields metadata already has:
    # - "name" ("Name")
    # - "type" ("Data type")
    # - "repeatable" ("Repeatable")
    # - "forbidden" and "mandatory" ("Legal Status")
    #
    # "Level" is replaced by "Business groups". "Fields not included in the legal text" isn't informative.
    overwrite = ['Description', 'Business groups']
    # Adding `compare={'name': 'Name'}` shows that the names agree, and differ mainly due to field:bt being m:1.
    df = write(filename, df, overwrite, left_on='btId', right_on='ID', validate='m:1')

    report(df, ['ID', 'Name'], ~df['ID'].isin({
        # Removed indicators in favor of corresponding scalars.
        # https://docs.ted.europa.eu/eforms/0.5.0/schema/all-in-one.html#extensionsSection
        'BT-53',  # Options (BT-54 Options Description)
        # https://docs.ted.europa.eu/eforms/0.5.0/schema/all-in-one.html#toolNameSection
        'BT-724',  # Tool Atypical (BT-124 Tool Atypical URL)
        # https://docs.ted.europa.eu/eforms/0.5.0/schema/all-in-one.html#_footnotedef_21
        'BT-778',  # Framework Maximum Participants (BT-113 Framework Maximum Participants Number)

        # Replaced by OPT-155 and OPT-156.
        # https://docs.ted.europa.eu/eforms/0.5.0/schema/competition-results.html#lotResultComponentsTable
        'BT-715',
        'BT-725',
        'BT-716',

        # See Table 3.
        # https://docs.ted.europa.eu/eforms/0.5.0/schema/parties.html#mappingOrganizationBTsSchemaComponentsTable
        'BT-08',
        'BT-770',

        # See Table 4 (also includes BT-330 and BT-1375).
        # https://docs.ted.europa.eu/eforms/0.5.0/schema/identifiers.html#pointlessDueToDesignSection
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
def update_with_2015_guidance(filename):
    """
    Update FILE with eForms XPaths and 2015 guidance.
    """

    def unique(value):
        return value.unique()

    def translate(value):
        return [df_strings.at[label, 'EN'] for label in value.unique() if pd.notna(label)]



    # See the "Legend" sheet for the data dictionary.
    with pd.ExcelFile(sourcedir / 'TED-XML-to-eForms-mapping-OP-public-20220404.xlsx') as xlsx:
        df = pd.read_excel(xlsx, 'tedxml_to_eforms_mapping.v0.4', na_values='---')

    # TODO: print unmatched TED Xpaths for review



    dfs = []
    for path in sorted(mappingdir.glob('*.csv')):
        df = pd.read_csv(path)

        # Add a "file" column for the source of the row.
        df['file'] = path.stem.split('_')[0]

        dfs.append(df)

    # ignore_index is required, as each data frame repeats indices.
    pd.concat(dfs, ignore_index=True)



    df_strings = pd.read_csv(sourcedir / 'Forms labels R2.09.csv').set_index('Label')

    # Aggregate XPaths per BT. This drops "BT Name" (duplicate) and "Additional information" (of no use).
    df_xpath = df_xpath.groupby('BT ID').agg({'XPATH': sorted})

    df_2015 = pd.read_csv(eformsdir / '2015-guidance.csv')
    # Remove rows with a "no index" index, as they won't merge below.
    df_2015 = df_2015[df_2015['index'] != 'no index']
    df_2015.rename(columns={'guidance': '2015 guidance'}, errors='raise', inplace=True)
    # This drops "xpath" and "comment", which are of no assistance to mapping.
    df_2015 = df_2015.groupby(['index']).agg({'2015 guidance': unique, 'label-key': translate, 'file': unique})

    # Start with the eForms file that contains indices used by the 2015 guidance.
    df = pd.read_csv(eformsdir / 'bt-indices-mapping.csv')
    df = df.merge(df_xpath, how='left', left_on='ID', right_on='BT ID')
    df = df.merge(df_2015, how='left', left_on='Level', right_on='index')
    # TODO: Print all Level that have no match, to see if any additional guidance can be imported

    # Add two manually-edited columns.
    # df.loc[df['2019 guidance'].notna(), 'status'] = 'imported from standard forms'
    df['comments'] = ''

    df.sort_values(['2019 form', '2015 form', 'ID'], inplace=True)

    df.drop(columns=[
        # bt-indices-mapping.csv: Defer these columns to the 2019 regulation's annex.
        # TODO: Test whether any of these are incorrect?
        'Indent level',
        'Name',
        'Data type',
        'Repeatable',
        'Description',
        'Legal Status',
    ], inplace=True)

    remove_colon_and_parentheses = re.compile(r':?(?: \([^)]+\))?$')

    # Check that the Level corresponds to the Element. The error is either in ted-xml-indices.csv or in bt-indices-mapping.csv.
    for label, row in df.iterrows():
        if row['Element'] is not np.nan and row['label-key'] is not np.nan:
            labels = [s.lower() for s in row['label-key'] if s not in ('yes', 'Date')]
            element = remove_colon_and_parentheses.sub('', row['Element'])
            if labels and element.lower() not in labels:
                click.echo(row['Level'], element, labels)

    write(filename, df)


@cli.command()
def statistics():
    """
    Print statistics on the progress of the guidance for the 2019 regulation.
    """
    df = pd.read_json(eformsdir / 'eforms-guidance.json', orient='records')

    df_terms = df.drop_duplicates(subset='ID')
    total_terms = df_terms.shape[0]
    done_terms = df_terms[df_terms['status'].str.startswith('done')].shape[0]

    total = df.shape[0]
    imported = df[df['status'] == 'imported from standard forms'].shape[0]
    done = df[df['status'].str.startswith('done')].shape[0]
    ready = imported + done
    no_issue_no_guidance = df[(df['status'] == '') & (df['guidance'] == '')].shape[0]

    df_issue = df[df['status'].str.startswith('issue')]
    issue = df_issue.shape[0]
    issue_no_guidance = df_issue[df_issue['guidance'] == ''].shape[0]

    legal_status = {}
    for value in ('M', 'O', ''):
        df_legal_status = df[df['Legal status'] == value]
        legal_status[value] = {
            'total': df_legal_status.shape[0],
            'done': df_legal_status[df_legal_status['status'].str.startswith('done')].shape[0],
            'issue': df_legal_status[df_legal_status['status'].str.startswith('issue')].shape[0],
        }

    click.echo(dedent(f"""\
    - BTs ready for review: {done_terms}/{total_terms} ({done_terms / total_terms:.1%})
    - Rows ready for review: {ready}/{total} ({ready / total:.1%})
        - Imported from 2015 guidance: {imported} ({imported / total:.1%})
        - Added or edited after import: {done} ({done / total:.1%})
        - Per legal status:
            - Mandatory: {legal_status['M']['done']}/{legal_status['M']['total']} ({legal_status['M']['done'] / legal_status['M']['total']:.1%}), {legal_status['M']['issue']} with open issues ({legal_status['M']['issue'] / legal_status['M']['total']:.1%})
            - Optional: {legal_status['O']['done']}/{legal_status['O']['total']} ({legal_status['O']['done'] / legal_status['O']['total']:.1%}), {legal_status['O']['issue']} with open issues ({legal_status['O']['issue'] / legal_status['O']['total']:.1%})
            - Empty: {legal_status['']['done']}/{legal_status['']['total']} ({legal_status['']['done'] / legal_status['']['total']:.1%}), {legal_status['']['issue']} with open issues ({legal_status['']['issue'] / legal_status['']['total']:.1%})
    - Rows with [open issues](https://github.com/open-contracting/european-union-support/labels/eforms): {issue} ({issue / total:.1%}), {issue_no_guidance} without guidance
    - Rows without issues and without guidance: {no_issue_no_guidance} ({no_issue_no_guidance / total:.1%})
    """))  # noqa: E501


@cli.command()
@click.argument('file', type=click.File())
def fields_without_extensions(file):
    """
    Print undefined fields in the guidance for the 2015 regulation.
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
