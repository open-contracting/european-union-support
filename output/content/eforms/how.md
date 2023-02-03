# How to use this profile

```{attention}
If you are not yet familiar with the eForms SDK, we recommend that you start with the [eForms Developer Guide](https://docs.ted.europa.eu/eforms/latest/guide/index.html).
```

The Publications Office of the European Union created the [eForms SDK](https://docs.ted.europa.eu/eforms/latest/) to facilitate eForms implementation. While it is possible to [implement eForms without the SDK](https://docs.ted.europa.eu/eforms/latest/guide/implementing-eforms-without-the-sdk.html), the Publications Office politely describes this as requiring ["several times the effort to create and maintain."](https://docs.ted.europa.eu/eforms/latest/guide/understanding-the-sdk.html#_the_purpose_of_the_eforms_sdk) We therefore map to OCDS from the metadata-driven SDK, not directly from the UBL/XML.

The eForms SDK introduces the concept of a [field](https://docs.ted.europa.eu/eforms/latest/fields/index.html). Each field corresponds to a business term defined in the [annex to the eForms regulation](https://single-market-economy.ec.europa.eu/single-market/public-procurement/digital-procurement/eforms_en). A same business term can have many corresponding fields, for each context in which the term is used: for example, the term *Title* (BT-21) can be used in the context of a lot, lot group, or part of a Prior Information Notice.

The [eForms Mapping](mapping) describes how to map each eForms SDK field to OCDS.

## Post-processing steps

These steps must be completed after using the [eForms Mapping](mapping) to construct an OCDS file.

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

## What's not included

[Notice types](https://github.com/OP-TED/eForms-SDK/blob/develop/notice-types/notice-types.json) X01 and X02 relate to events outside the lifecycle of a contracting process.

* X01 - Notice containing information relevant to Formation or Completion of the liquidation of a [EEIG](https://en.wikipedia.org/wiki/European_economic_interest_grouping)
* X02 - Notice containing information about Registration, Deletion, Transfer-registration or Transfer-deletion of a European Company or European Cooperative Society

Furthermore, thee following notice types are listed in the regulation's annex but are not described by the eForms SDK.

- E1 - Prior market consultation notice
- E5 - Contract completion notice type

Therefore, fields that are only used in these notice types are omitted from the guidance.

```{dropdown} Omitted fields
For X01 and/or X02:

- BT-500-Business
- BT-501-Business-European
- BT-501-Business-National
- BT-502-Business
- BT-503-Business
- BT-505-Business
- BT-506-Business
- BT-507-Business
- BT-510(a)-Business
- BT-510(b)-Business
- BT-510(c)-Business
- BT-512-Business
- BT-513-Business
- BT-514-Business
- BT-739-Business
- OPP-100-Business
- OPP-105-Business
- OPP-110-Business
- OPP-111-Business
- OPP-112-Business
- OPP-113-Business-European
- OPP-120-Business
- OPP-121-Business
- OPP-122-Business
- OPP-123-Business
- OPP-130-Business
- OPP-131-Business

For E1:

- BT-800(d)-Lot
- BT-800(t)-Lot

For E5:

- BT-779-Tender
- BT-780-Tender
- BT-781-Lot
- BT-782-Tender
- BT-783-Review
- BT-784-Review
- BT-785-Review
- BT-786-Review
- BT-787-Review
- BT-788-Review
- BT-789-Review
- BT-790-Review
- BT-791-Review
- BT-792-Review
- BT-793-Review
- BT-794-Review
- BT-795-Review
- BT-796-Review
- BT-797-Review
- BT-798-Review
- BT-799-ReviewBody
- OPT-091-ReviewReq
- OPT-092-ReviewBody
- OPT-092-ReviewReq
- OPT-301-ReviewBody
- OPT-301-ReviewReq
```

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
