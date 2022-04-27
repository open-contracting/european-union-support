#!/usr/bin/env python
import csv
import re
import shutil
from io import StringIO
from pathlib import Path
from textwrap import dedent
from zipfile import ZipFile

import click
import pandas as pd

basedir = Path(__file__).resolve().parent
sourcedir = basedir / 'source'
mappingdir = basedir / 'output' / 'mapping'


def excel_files():
    with ZipFile(sourcedir / 'Task 5_Support_Standard Forms-eForms mappings_v.3.zip') as zipfile:
        for name in zipfile.namelist():
            with zipfile.open(name) as fileobj:
                with pd.ExcelFile(fileobj) as xlsx:
                    yield name, xlsx

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
def xlsx2csv():
    """
    Extract CSV files from XLSX files.
    """
    outdir = sourcedir / 'eForms'

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

    # Create a fresh output directory.
    shutil.rmtree(outdir)
    outdir.mkdir()

    explode = ['Level', 'Element']

    for name, xlsx in excel_files():
        for sheet in xlsx.sheet_names:
            if sheet in ignore or any(regex.search(sheet) for regex in ignore_regex):
                continue

            match = keep.search(sheet)
            if not match:
                raise click.ClickException(f"The sheet name {sheet!r} doesn't match a known pattern.")

            filename = f'eForm{match.group(1).rjust(2, "0")} vs SF{match.group(2)}.csv'

            # Read the Excel file. The first row is a title for the table.
            df = pd.read_excel(xlsx, sheet, skiprows=[0])

            # Avoid empty or duplicate headings.
            df.rename(columns={
                df.columns[0]: 'Empty',  # was "" ("Unnamed: 0" after `read_excel`)
                df.columns[1]: 'Indent level',  # was "Level" or "" ("Unnamed: 1" after `read_excel`)
                df.columns[8]: 'Level',  # "Level.1" after `read_excel` if column 1 was "Level"
            }, errors='raise', inplace=True)

            # The first column is empty.
            if df['Empty'].isna().all():
                df.drop(columns='Empty', inplace=True)
            else:
                raise click.ClickException(f"The first column was expected to be empty.")

            # Make values easier to work with (must occur after `isna` above).
            df.fillna('', inplace=True)

            # `explode` requires lists with the same number of elements, but an "Element" is not repeated if it is
            # the same for all "Level". Extra newlines also complicate things.
            for _, row in df.iterrows():
                location = f'{filename}: {row["ID"]}: '

                # Remove spurious newlines in "Element" values.
                row['Element'] = re.sub(r'\n(?=[a-z(]|Title\b|2009\b)', ' ', row['Element'].replace('\n\n', '\n'))

                # Hardcode corrections or cases requiring human interpretation.
                if (filename == 'eForm15 vs SF07.csv'
                    and row['ID'] == 'BT-18'
                    and row['Level'] == 'I.3.4.1.1'
                    and len(row['Element'].split('\n')) == 2
                ):
                    row['Level'] = 'I.3.4.1.1\nI.3.4.1.2'
                elif (
                    filename == 'eForm18 vs SF17.csv'
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

                # Remove leading and trailing newlines (occurs in "Level" values), then split.
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
                raise click.ClickException(f'{filename}: {e}')

            # Prepare the CSV contents.
            io = StringIO()
            df.to_csv(io, sep=';', index=False)
            output = io.getvalue()

            # Write the CSV file.
            path = outdir / filename
            if path.exists():
                click.secho(f'{filename} ({sheet}) overwritten from {name}', fg='yellow')
            with path.open('w') as f:
                f.write(output)


@cli.command()
def concatenate():
    """
    Create the concatenated.csv file.

    \b
    - Concatenate the CSV files for the 2015 regulation.
    - Merge the standard-form-element-identifiers.csv file, which replaces the index column with a new identifier.
    """
    identifiers = pd.read_csv(mappingdir / 'eForms' / 'standard-form-element-identifiers.csv')

    concat = pd.DataFrame()
    for path in mappingdir.glob('*.csv'):
        # The other columns are "index" and "comment".
        df = pd.read_csv(path, usecols=['xpath', 'guidance', 'label-key'])
        # Add the "index" column from the identifiers file.
        df = pd.merge(df, identifiers, how='left', on='xpath')
        # Add a "file" column for the source of the row.
        df['file'] = path.name
        concat = pd.concat([concat, df], ignore_index=True)

    concat.to_csv(
        mappingdir / 'shared' / 'concatenated.csv',
        columns=['xpath', 'label-key', 'index', 'guidance', 'file']
    )

    # TODO: There are a few exceptions to "guidance" being identical across all forms.
    concat.drop_duplicates(['xpath', 'label-key', 'index'], ignore_index=True, keep='first', inplace=True)

if __name__ == '__main__':
    cli()
