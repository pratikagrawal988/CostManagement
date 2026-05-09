# Excluded Files

This lean package excludes `data/csp_catalog/` from the full export. That directory contained Product Catalog builders, config, raw cache, and generated output, and accounted for roughly 765 MB unpacked.

The recommendation engine SPA, mocks, recommendation CSVs, PM docs, architecture docs, CostVars source document, and extraction script are still included.
