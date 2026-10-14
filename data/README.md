# Approved local data only

Store the supplied workbook under data/local and read the original ZIP from its approved local location. Do not add raw extracts, archives, predictions, derived outputs or data-backed workbooks to Git.

The complete supplied ZIP and earlier outcome-stratified workbook support different analysis populations. See docs/DATASET_CARD.md for provenance and limitations.

Synthetic fixtures are generated under the ignored runtime directory and never read the confidential archive. No cloud data upload is authorized.
