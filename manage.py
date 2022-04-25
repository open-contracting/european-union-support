#!/usr/bin/env python
from pathlib import Path

import click
import pandas as pd


@click.group()
def cli():
    pass


@cli.command()
def concatenate():
    """
    Create the concatenated.csv file.

    \b
    - Concatenate the CSV files for the 2015 regulation.
    - Merge the standard-form-element-identifiers.csv file, which replaces the index column with a new identifier.
    """
    directory = Path(__file__).resolve().parent.parent / 'output' / 'mapping'

    identifiers = pd.read_csv(directory / 'eForms' / 'standard-form-element-identifiers.csv')

    concat = pd.DataFrame()
    for path in directory.glob('*.csv'):
        # The other columns are "index" and "comment".
        df = pd.read_csv(path, usecols=['xpath', 'guidance', 'label-key'])
        # Add the "index" column from the identifiers file.
        df = pd.merge(df, identifiers, how='left', on='xpath')
        # Add a "file" column for the source of the row.
        df['file'] = path.name
        concat = pd.concat([concat, df], ignore_index=True)

    concat.to_csv(
        directory / 'shared' / 'concatenated.csv',
        columns=['xpath', 'label-key', 'index', 'guidance', 'file']
    )

    # TODO: There are a few exceptions to "guidance" being identical across all forms.
    concat.drop_duplicates(['xpath', 'label-key', 'index'], ignore_index=True, keep='first', inplace=True)


if __name__ == '__main__':
    cli()
