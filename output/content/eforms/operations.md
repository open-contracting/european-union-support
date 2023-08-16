# Common operations

```{admonition} Summary
To avoid repetition in the [Field mappings](mapping), we refer and link to the following common operations.
```

## Create a release

If the notice is a prior information or periodic indicative notice used only for information (PIN only), you should repeat the following steps for each part (`/*/cac:ProcurementProjectLot[cbc:ID/@schemeName='Part']`) because each part is treated as a separate planning process. Otherwise, you need only perform the steps once per notice.

1. Create an empty JSON object
1. Set its [`id`](https://standard.open-contracting.org/latest/en/schema/identifiers/#release-id) to the notice identifier (`/*/cbc:ID`).
1. Set its `initiationType` to 'tender'.
1. Set its `ocid` as described below.

If any of the following are true, assign a new `ocid` by prepending your [OCID prefix](https://standard.open-contracting.org/latest/en/guidance/build/#register-an-ocid-prefix) to a unique identifier of your choice (e.g. a [version 4 UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier) or a suitable system-internal identifier):

* The notice is the first publication concerning the procedure.
* The notice is a contract award notice (CAN) for an award within a framework agreement or dynamic purchasing system.
* The previous publication concerning the procedure is a PIN only notice. Notices following a PIN only notice are assigned a new `ocid` because they may be defined based on multiple parts.

Otherwise, set `ocid` to the same value as the previous publication's `ocid`.

## Reference a previous publication

If the *Previous publication concerning this procedure* is neither a prior information notice nor a periodic indicative notice (PIN), or if the PIN has a single `/*/cac:ProcurementProjectLot` (*Object*) element, then discard `/*/cbc:ID`. In this case, the *previous publication concerning this procedure* is the OCDS release with the same `ocid` as this release and with the nearest earlier `date` to this release.

Otherwise, if the *Previous publication concerning this procedure* is a prior information notice or periodic indicative notice that has multiple `/*/cac:ProcurementProjectLot` (*Object*) elements, add a `RelatedProcess` object to the `relatedProcesses` array, set its `.id` to '1', add 'planning' to its `.relationship` array, set its `.scheme` to 'eu-oj' (or to a scheme of your choice if outside the EU), and map `/*/cbc:ID` to `.identifier`.

## Convert a date to ISO format

[OCDS dates](https://standard.open-contracting.org/latest/en/schema/reference/#date) must be formatted according to ISO 8601 and include a time component.

If a time component is missing from a date, use 'T23:59:59Z' for end dates and 'T00:00:00Z' for other dates.

If a timezone component is present in the date (e.g. '+02:00'), preserve it. Otherwise, use the UTC timezone indicate 'Z'.

The final value would be '2020-10-21T23:59:59Z' or '2020-10-21T00:00:00Z'.

## Add a complaints statistic

Add a `Statistic` object to the `statistics` array, set its `.relatedLot` to the value of `ancestor::efac:LotResult/efac:TenderLot/cbc:ID`, set its `scope` to 'complaints', and set its `.id` (string) sequentially across all notices for this procedure. For example, if a first notice for a given procedure has nine statistics, it uses `id`'s '1' through '9'. A second notice for the same procedure then uses `id`'s '10' and up, etc.

## Add a bids statistic

Add a `Statistic` object to the `bids.statistics` array, set its `.relatedLot` to the value of `ancestor::efac:LotResult/efac:TenderLot/cbc:ID`, and set its `.id` (string) sequentially across all notices for this procedure. For example, if a first notice for a given procedure has nine bid statistics, it uses `id`'s '1' through '9'. A second notice for the same procedure then uses `id`'s '10' and up, etc.

## Get the document for a document reference

Get the `Document` object in `tender.documents` whose `.id` is equal to the document reference's `/cbc:ID`. If none exists yet, add a `Document` object to `tender.documents` and set its `.id` to the document reference's `/cbc:ID`.

## Get the participation fee for a document

If the value of `ancestor::cac:ProcurementProjectLot[cbc:ID/@schemeName]` is `'Part'`, get the `ParticipationFee` object in `tender.participationFees` whose `.id` is equal to `cac:CallForTendersDocumentReference/cbc:ID`. If none exists yet, add a `ParticipationFee` object to `tender.participationFees` and set its `.id` to the value of `ancestor::cac:CallForTendersDocumentReference/cbc:ID`.

If the value of `ancestor::cac:ProcurementProjectLot[cbc:ID/@schemeName]` is `'Lot'`, [get the lot for the ProcurementProjectLot](operations.md#get-the-lot-for-a-procurementprojectlot) and get the `ParticipationFee` object in the lot's `.participationFees` whose `.id` is equal to `cac:CallForTendersDocumentReference/cbc:ID`. If none exists yet, add a `ParticipationFee` object to the lot's `.participationFees` and set its `.id` to the value of `ancestor::cac:CallForTendersDocumentReference/cbc:ID`.

## Get a translation

Download 'business-term_XX.xml' from [eForms SDK translations](https://github.com/OP-TED/eForms-SDK/tree/develop/translations) for the language required, where XX is the 2 letter language code. Find the row with the key 'business-term|description|BT-##' for the business term required (for example 'business-term|description|BT-160') and take the value from the entry.

## Parties

### Add a party

Add an `Organization` object to the `parties` array, and set its `.id` (string). **A party's `.id` needs to be consistent across all notices.** It is recommended to implement a register of organization identifiers to assign consistent identifiers. For more information, [see the OCDS documentation](https://standard.open-contracting.org/latest/en/schema/identifiers/#organization-ids).

### Get the organization for a company

Get the `Organization` in `parties` whose `id` is equal to the value of `ancestor::efac:Organization/efac:Company/cac:PartyIdentification/cbc:ID`. If none exists yet:

1. Add an `Organization` to `parties`
1. Set its `.id` to the value of the `ancestor::efac:Organization/efac:Company/cac:PartyIdentification/cbc:ID`.

### Get the organization for a touchpoint

Get the `Organization` in `parties` whose `id` is equal to the value of `ancestor::efac:TouchPoint/cac:PartyIdentification/cbc:ID`. If none exists yet:

1. Add an `Organization` to `parties`
1. Set its `.id` to the value of `ancestor::efac:TouchPoint/cac:PartyIdentification/cbc:ID`
1. Set its `.identifier.id` to the value of `ancestor::efac:Organization/efac:Company/cac:PartyLegalEntity/cbc:CompanyID`
1. [Set its `.identifier.scheme`](https://standard.open-contracting.org/1.1/en/schema/identifiers/#organization-ids).

### Get the organization for the buyer

Get the Organization in `parties` whose `.id` is equal to the value of `ancestor::cac:ContractingParty/cac:Party/cac:PartyIdentification/cbc:ID`. If none exists yet:

1. Add an `Organization` to `parties` 
1. Set its `.id` to the value of `ancestor::cac:ContractingParty/cac:Party/cac:PartyIdentification/cbc:ID`
1. Add 'buyer' to it's `.roles`

### Get the organization for a tenderer

Get the Organization in `parties` whose `.id` is equal to the value of `ancestor::efac:TenderingParty/efac:Tenderer/cbc:ID`. If none exists yet:

1. Add an `Organization` to `parties` 
1. Set its `.id` to the value of `ancestor::efac:TenderingParty/efac:Tenderer/cbc:ID`
1. Add 'tenderer' to it's `.roles`

### Get the person for an ultimate beneficial owner

Get the `Organization` in `parties` whose `id` is equal to the value of `ancestor::efac:Organization/efac:Company/cac:PartyIdentification/cbc:ID`. If none exists yet:

1. Add an `Organization` to `parties`
1. Set its `.id` to the value of `ancestor::efac:Organization/efac:Company/cac:PartyIdentification/cbc:ID`.

Get the `Person` in the organization's `.beneficialOwners` array whose `id` is equal to the value of `ancestor::efac:UltimateBeneficialOwner/cbc:ID`. If none exists yet:

1. Add a `Person` to `.beneficialOwners`
1. Set its `.id` to the value of `ancestor::efac:UltimateBeneficialOwner/cbc:ID`.

```{note}
`ancestor::efac:UltimateBeneficialOwner/cbc:ID` is assumed to be a unique within the scope of the contracting process.
```

### Get the organization for an organization technical identifier reference

Get the `Organization` object in `parties` whose `.id` is equal to the organization technical identifier reference's `/cbc:ID`. If none exists yet, add an `Organization` object to `parties` and set its `.id` to the organization technical identifier reference's `/cbc:ID`.

## Lots and items

### Get the lot for a ProcurementProjectLot

Get the `Lot` in `tender.lots` whose `.id` is equal to the value of `ancestor::cac:ProcurementProjectLot/cac:ID`. If none exists yet, add a `Lot` to `tender.lots` and set its `id` to the value of `ancestor::cac:ProcurementProjectLot/cac:ID`.

### Get the lot group for a ProcurementProjectLot

Get the `LotGroup` in `tender.lotGroups` whose `.id` is equal to the value of the XPath `ancestor::cac:ProcurementProjectLot/cac:ID`. If none exists yet, add a `LotGroup` to `tender.lotGroups` and set its `id` to the value of the XPath `ancestor::cac:ProcurementProjectLot/cac:ID`.

### Get the item for a ProcurementProjectLot

Get the `Item` in `tender.items` whose `.relatedLot` is equal to the value of `ancestor::cac:ProcurementProjectLot/cac:ID`. If none exists yet, add an `Item` to `tender.items`, set its `.id` incrementally and set its `.relatedLot` to the value of `ancestor::cac:ProcurementProjectLot/cac:ID`.

### Get the lot for a LotResult

Get the `Lot` in `tender.lots` whose `id` is equal to the value of `ancestor::efac:LotResult/efac:TenderLot/cbc:ID`. If none exists yet, add a `Lot` to `tender.lots` and set its `id` to the value of `ancestor::efac:LotResult/efac:TenderLot/cbc:ID`.

### Get the lots for a SettledContract

For each `ancestor::efac:NoticeResult/efac:LotResult` with a `/SettledContract` equal to the value of `ancestor::efac:SettledContract/cbc:ID`, get the `Lot` in `tender/lots` whose `.id` is equal to the value of the `LotResult`'s `/efac:TenderLot/cbc:ID`.

### Get the lot for a LotTender

Get the `Lot` object in `tender.lots` whose `.id` matches `ancestor::efac:LotTender/efac:TenderLot:cbc:ID`. If none exists yet, add a `Lot` to `tender.lots` and set its `id` to the value of `ancestor::efac:LotTender/efac:TenderLot:cbc:ID`.

## Bids, awards and contracts

### Get the bid for a LotTender

Get the `Bid` in `bids` whose `id` is equal to the value of `ancestor::efac:LotTender/cbc:ID`. If none exists yet:

1. Add a `Bid` to `bids`
1. Set its `.id` to the value of `ancestor::efac:LotTender/cbc:ID`
1. Add the value of `ancestor::efac:LotTender/efac:TenderLot/cbc:ID` to its `.relatedLots`

### Get the award for a LotResult

Get the `Award` in `awards` whose `id` is equal to the value of `ancestor::efac:LotResult/cbc:ID`. If none exists yet:

1. Add an `Award` to `awards`
1. Set its `.id` to the value of `ancestor::efac:LotResult/cbc:ID`
1. Add the value of `ancestor::efac:LotResult/efac:TenderLot/cbc:ID` to its `.relatedLots`

### Get the contract for a SettledContract

Get the `Contract` in `contracts` whose `.id` is equal to `ancestor::efac:SettledContract/cbc:ID`. If none exists yet:

1. Add a `Contract` to `contracts`
1. Set its `.id` to the value of `ancestor::efac:SettledContract/cbc:ID`
1. Get all LotResults (`ancestor::efac:NoticeResult/efac:LotResult`) with an `/efac:SettledContract/cbc:ID` equal to `ancestor::efac:SettledContract/cbc:ID`
  1. If there is exactly one, add its `/cbc:ID` to the contract's `.awardID`
  1. If there is more than one, add each LotResult's `/cbc:ID` to the contract's `.awardIDs`
