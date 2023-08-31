# How to use this profile

## Convert a notice to OCDS format

[Create a release](operations.md#create-a-release) and map each field on the notice according to the [field mappings](mapping).

## Post-processing steps

These steps must be completed after using the [Field mappings](mapping) to construct an OCDS file.

### Populate `.name` in organization references

For each `OrganizationReference` object in your data, get the `Organization` in `parties` whose `.id` is equal to the `.id` of the organization reference and set the organization reference's `.name` to the `.name` of the organization. The following fields are `OrganizationReference` objects:

* `buyer`
* `planning/budget/finance/financingParty`
* `tender/documents/publisher`
* `tender/lots/designContest/selectedParticipants`
* `bids/details/tenderers`
* `bids/details/subcontracting/subcontracts/subcontractor`
* `bids/details/subcontracting/subcontracts/tenderers`
* `awards/suppliers`
* `awards/buyers`

## Post-publication steps

These steps must be completed at the described time after publishing an OCDS file.

### Release withheld information

Some information required by eForms may remain non-public ("unpublished") for a defined period, as described in [withheld publication of information](https://docs.ted.europa.eu/eforms/latest/schema/withheld-publication.html). Whereas, with eForms, Tenders Electronic Daily can take responsibility for publishing the withheld information on the desired date, with OCDS, you must take responsibility.

For fields with an associated `efac:FieldsPrivacy` element, wait until the date in `/efbc:PublicationDate` and then:

* [Create a release](operations.md#create-a-release) and add 'previouslyWithheldInformation' to its `.tag` array.
* Perform the mapping for the fields and publish the release.

## Data use

```{admonition} Summary
This section describes how to interpret OCDS data that conforms to this profile.
```

### Framework agreements with multiple winners (cascades)

Suppliers are in a cascade if:

* The tender or lot uses a framework agreement (`.techniques.hasFrameworkAgreement` is `true`); and
* The award has multiple suppliers (`.suppliers` contains more than one `OrganizationReference`); and
* Bids have ranks (`bids.details.hasRank` is `true`).

The rank of each bid might be available in `bids.details.rank`.
