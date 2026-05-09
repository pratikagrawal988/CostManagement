# FinOps Recommendation Engine Export

Generated: 2026-04-30 12:52 IST

This package contains the Basic FinOps Recommendation Engine assets needed to move the mock/product package into a new project.

## Included

- `web/FinOps Recommendation Engine/` - standalone SPA mock, local React/Babel libraries, docs, sample recommendation JS, and CSV data.
- `pm/features/finops-recommendation-engine/` - PRD, roadmap, user guide, recommendation catalogs, CostVars advisory mapping, compatibility groups, integration guide, and review docs.
- `docs/architecture/finops-recommendation-engine.md` - technical architecture.
- `cost_advisory/` - related cost advisory schema, governance policies, and recommendation CSVs.
- `docs/optimization/` - related recommendation and GPU optimization docs.
- `web/Cost Recommendations Related/` - related legacy recommendation page mocks.
- `source-docs/FinOps_CostVars_Tooling_v2.docx` - source advisory document used to create CVAR mappings.
- `tools/extract_costvars_docx.py` - reproducible DOCX extraction logic.
- `extracted/costvars_docx_paragraphs.txt` - raw paragraph extraction from the DOCX.
- `EXPORT_MANIFEST.csv` - complete file list, sizes, and SHA-256 hashes.
- `LARGE_FILES.md` - files and folders that may make the zip large.

## Run the SPA

From the extracted package root:

```bash
cd web
python3 -m http.server 5173
```

Open:

```text
http://127.0.0.1:5173/FinOps%20Recommendation%20Engine/
```

## Notes

This lean export intentionally excludes `data/csp_catalog/` because those Product Catalog cache/output files made the package large. Product Catalog behavior is still represented in the SPA mock, PM docs, and recommendation CSV fields, but the raw builders/cache/output are not included.


## Excluded From This Lean Zip

- `data/csp_catalog/` - Product Catalog builders, cache, and generated raw output. This removed roughly 765 MB unpacked from the export.
