### General guidance for `/CHANGES/CHANGE`

The fields of sections VII related to changes to a published notice (F14 "Corrigendum") do not directly map to OCDS fields. They require general instructions instead of field by field guidance.

Each change (`/CHANGES/CHANGE`) bears all the information required to determine how to translate the change in OCDS, whether it modifies text, a CPV code or a date.

#### Using the OCDS HTML mapping tables

    1. If the form is not in English, using the "Place of text to be modified" (`/CHANGES/CHANGE/WHERE/LABEL`) and the language of the form (`/@LG`), determine the English label for the value to map. You can use column the [Forms label spreadsheet](https://publications.europa.eu/documents/3938058/5358176/Forms_Labels_R209.zip/6e5fa3bc-62bf-0b66-0ae2-c1979d445355) (the English label is in column D).
    2. Using the English label, find the corresponding mapping guidance in [the OCDS HTML mapping tables](https://standard.open-contracting.org/profiles/eu/master/en/#ted-and-ocds). Use the "Section number" (`/CHANGES/CHANGE/WHERE/SECTION`) to disambiguate if there are multiple matches for the English label.

    If the English label has no guidance, take the guidance for the labels that follow. For example, for "Estimated total value", take the guidance for "Value excluding VAT" and "Currency".

    If the OCDS guidance pertains to a lot, use the "Lot No" (`/CHANGES/CHANGE/WHERE/LOT_NO`) to determine the "Lot object" in `tender.objects` with a matching `.id`.

    3. Apply the OCDS guidance.

#### Programmatically

    1. Using the "Place of text to be modified" (`/CHANGES/CHANGE/WHERE/LABEL`) and the language of the form (`/@LG`), determine the label key for the value to map. You can use column the [Forms label spreadsheet](https://publications.europa.eu/documents/3938058/5358176/Forms_Labels_R209.zip/6e5fa3bc-62bf-0b66-0ae2-c1979d445355) (the label key is in column A).
    2. Using the label key, find the corresponding mapping guidance in [the OCDS mapping CSVs](https://github.com/open-contracting/european-union-support/tree/master/output/mapping). Use the "Section number" (`/CHANGES/CHANGE/WHERE/SECTION`) to disambiguate if there are multiple matches for the label key.

    If the label key has no guidance, take the guidance for the labels that follow. For example, for `value_magnitude_estimated_total`, take the guidance for `value_excl_vat` and `currency`.

    If the OCDS guidance pertains to a lot, use the "Lot No" (`/CHANGES/CHANGE/WHERE/LOT_NO`) to determine the "Lot object" in `tender.objects` with a matching `.id`.

    3. Apply the OCDS guidance.
