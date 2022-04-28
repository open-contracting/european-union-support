#!/usr/bin/env python
import csv
import re
from io import StringIO
from pathlib import Path
from textwrap import dedent
from zipfile import ZipFile

import click
import pandas as pd
from docx import Document

basedir = Path(__file__).resolve().parent
sourcedir = basedir / 'source'
mappingdir = basedir / 'output' / 'mapping'


def excel_files():
    with ZipFile(sourcedir / 'Task 5_Support_Standard Forms-eForms mappings_v.3.zip') as zipfile:
        for name in zipfile.namelist():
            with zipfile.open(name) as fileobj:
                with pd.ExcelFile(fileobj) as xlsx:
                    yield name, xlsx


def text(row):
    # Newlines occur in all columns except the first, e.g.:
    # /*/cac:ContractingParty/cac:ContractingRepresentationType/cbc:RepresentationTypeCode
    # /*/cac:ProcurementProjectLot/cac:TenderingTerms/cac:TenderRecipientParty/cbc:EndpointID
    # Leading or trailing whitespace occur in the first and third columns, e.g.:
    # /*/cac:ProcurementProjectLot/cac:ProcurementProject/cbc:EstimatedOverallContractQuantity
    # /*/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:Change/efbc:ChangedNoticeIdentifier
    cells = [cell.text.replace('\n', ' ').strip() for cell in row.cells]
    # Correct a typo.
    cells[0] = cells[0].replace('[@n listName=', '[@listName=')
    return cells


@click.group()
def cli():
    pass


@cli.command()
@click.argument('sheet')
def find(sheet):
    """
    Find the workbook containing the SHEET.
    """
    for name, xlsx in excel_files():
        if sheet in xlsx.sheet_names:
            click.echo(f'First occurrence: {name}')
            break
    else:
        click.secho(f"Sheet '{sheet}' not found", fg='red')


@cli.command()
def extract_docx():
    """
    Extract CSV file from DOCX file.
    """
    docx = Document(sourcedir / 'XPATHs provisional release v. 1.0.docx')

    length = len(docx.tables)
    assert length == 1, f'unexpected table, found {length}'

    columns = text(docx.tables[0].rows[0])
    assert columns == ['XPATH', 'BT ID', 'BT Name', 'Additional information'], f'unexpected headers, got {columns}'

    data = []
    for row in docx.tables[0].rows[1:]:
        cells = text(row)
        xpath = cells[0]
        # Skip subheadings.
        if not xpath.startswith('/'):
            continue
        data.append(cells)

    df = pd.DataFrame(data, columns=['eforms_xpath', 'bt', 'name', 'notes'])

    df.to_csv(mappingdir / 'eForms' / 'xpath_bt_mapping.csv', index=False)


@cli.command()
def extract_xlsx():
    """
    Extract CSV files from XLSX files.
    """
    ignore = {
        'Annex table 2',
        'eN40 vs F20',
        'Legend',
        'Legend Annex table 2',
        'S.F. vs eForms mapping list ',
    }
    ignore_regex = [re.compile(pattern) for pattern in (
        r'^F\d\d vs eN\d\d( \(2\))?$',
        r'^SF\d\d vs eForm ?\d\d(,\d\d)*$'
    )]
    keep = re.compile(r'^(?:eForm|eN) ?(\d\d?(?:,\d\d)*) vs S?F(\d\d ?)$')

    overrides = {
        'III.2.1.1.1': 'Information and formalities necessary for evaluating if the requirements are met:',
        'III.2.2.2': 'Information and formalities necessary for evaluating if the requirements are met:',
        'III.2.2.3': 'Minimum level(s) of standards possibly required: (if applicable)',
        'III.2.3.1.1': 'Information and formalities necessary for evaluating if the requirements are met:',
        'III.2.3.1.2': 'Minimum level(s) of standards possibly required: (if applicable)',
    }

    explode = ['Level', 'Element']

    dfs = []
    for name, xlsx in excel_files():
        for sheet in xlsx.sheet_names:
            if sheet in ignore or any(regex.search(sheet) for regex in ignore_regex):
                continue

            match = keep.search(sheet)
            if not match:
                raise click.ClickException(f"The sheet name {sheet!r} doesn't match a known pattern.")

            eforms_notice_number = match.group(1)
            sf_notice_number = match.group(2).lstrip('0')

            # Read the Excel file. The first row is a title for the table.
            df = pd.read_excel(xlsx, sheet, skiprows=[0])

            # Avoid empty or duplicate headings.
            df.rename(columns={
                df.columns[0]: 'Empty',  # was "" ("Unnamed: 0" after `read_excel`)
                df.columns[1]: 'Indent level',  # was "Level" or "" ("Unnamed: 1" after `read_excel`)
                df.columns[8]: 'Level',  # "Level.1" after `read_excel` if column 1 was "Level"
            }, errors='raise', inplace=True)

            # Remove rows without "Level", for which we have no mapping information.
            df = df[df['Level'].notna()]

            # Remove the first column if it is empty.
            if df['Empty'].isna().all():
                df.drop(columns='Empty', inplace=True)
            else:
                raise click.ClickException(f"The first column was expected to be empty.")

            # Add notice number columns, using '1' instead of '01' to ease joins with forms_noticeTypes.csv.
            df['eformsNotice'] = [[number.lstrip('0') for number in eforms_notice_number.split(',')] for i in df.index]
            df['sfNotice'] = sf_notice_number

            # Make values easier to work with (must occur after `isna` above).
            df.fillna('', inplace=True)

            # `explode` requires lists with the same number of elements, but an "Element" is not repeated if it is
            # the same for all "Level". Extra newlines also complicate things.
            for _, row in df.iterrows():
                location = f'eForm {eforms_notice_number} - SF {sf_notice_number}: {row["ID"]}: '

                # Remove spurious newlines in "Element" values.
                row['Element'] = re.sub(r'\n(?=[a-z(]|Title\b|2009\b)', ' ', row['Element'].replace('\n\n', '\n'))

                # Hardcode corrections or cases requiring human interpretation.
                if (
                    eforms_notice_number == '15'
                    and sf_notice_number == '7'
                    and row['ID'] == 'BT-18'
                    and row['Level'] == 'I.3.4.1.1'
                    and len(row['Element'].split('\n')) == 2
                ):
                    row['Level'] = 'I.3.4.1.1\nI.3.4.1.2'
                elif (
                    eforms_notice_number == '18'
                    and sf_notice_number == '17'
                    and row['ID'] == 'BT-750'
                    and row['Level'] == 'III.2.1.1.1\nIII.2.2.2\nIII.2.2.3\nIII.2.3.1.1\nIII.2.3.1.2'
                    and len(row['Element'].split('\n')) == 2
                ):
                    row['Element'] = dedent("""\
                    Information and formalities necessary for evaluating if the requirements are met:
                    Information and formalities necessary for evaluating if the requirements are met:
                    Minimum level(s) of standards possibly required: (if applicable)
                    Information and formalities necessary for evaluating if the requirements are met:
                    Minimum level(s) of standards possibly required: (if applicable)
                    """)

                if '\n' not in row['Level']:
                    # Warn about remaining newlines (BT-531 twice).
                    if '\n' in row['Element']:
                        click.secho(f'{location}unexpected \\n in "Element": {repr(row["Element"])}', fg='yellow')
                    continue

                # Split values, after removing leading and trailing newlines (occurs in "Level" values).
                for column in explode:
                    row[column] = row[column].strip("\n").split("\n")

                # Repeat "Element" as many times as there are "Level".
                length = len(row['Level'])
                if length > len(row['Element']):
                    row['Element'] *= length
                if length != len(row['Element']):
                    click.secho(f'{location}size differs: {row["Level"]} {row["Element"]}', fg='red')

            try:
                df = df.explode(explode)
            except ValueError as e:
                raise click.ClickException(f'{sheet}: {e}')

            df = df.explode('eformsNotice')

            dfs.append(df)

    pd.concat(dfs, ignore_index=True).to_csv(mappingdir / 'eForms' / 'extract.csv')


@cli.command()
def concatenate():
    """
    Create the concatenated.csv file.

    \b
    - Concatenate the CSV files for the 2015 regulation.
    - Merge the standard-form-element-identifiers.csv file, which replaces the index column with a new identifier.
    """
    identifiers = pd.read_csv(mappingdir / 'eForms' / 'standard-form-element-identifiers.csv')

    dfs = []
    for path in mappingdir.glob('*.csv'):
        # The other columns are "index" and "comment".
        df = pd.read_csv(path, usecols=['xpath', 'label-key', 'guidance'])
        # Add the "index" column from the identifiers file.
        df = pd.merge(df, identifiers, how='left', on='xpath')
        # Add a "file" column for the source of the row.
        df['file'] = path.name
        dfs.append(df)

    # ignore_index is required, as each data frame repeats indices. Re-order the columns.
    pd.concat(dfs, ignore_index=True).to_csv(
        mappingdir / 'shared' / 'concatenated.csv',
        columns=['xpath', 'label-key', 'index', 'guidance', 'file']
    )


if __name__ == '__main__':
    cli()
