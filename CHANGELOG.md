# Changelog

## Spec v1.1 — 2026-11-02

[VERIFY] items checked against live services. Differences from spec v1:

- **ADMIN-EXPRESS COG CARTO**: latest edition is 4.0 (2026-01-01). Layer names are now lowercase (`region`, `departement`), and fields are renamed: `code_insee`, `nom_officiel`, `code_insee_de_la_region`. The old names `INSEE_REG`, `INSEE_DEP` and `NOM` no longer exist. The source is now the France-wide FlatGeobuf in WGS84, filtered to metropolitan France.
- **GFW DIST-ALERT API**:
  - Fields are named `umd_glad_dist_alerts__date`, `umd_glad_dist_alerts__confidence` (2/3/4) and `area__ha`.
  - The SQL table name is `results`.
  - The forest filter is available as `umd_tree_cover_density_2000__threshold` (a coded class, not a percentage).
  - Queries require an `x-api-key`.
- **DIST-ALERT tiles**: the confidence parameter is `alert_confidence=low|high`. Their tree-cover filter uses 2010 tree cover density.
- **Hansen GEE asset** `UMD/hansen/global_forest_change_2025_v1_13`: confirmed, still the latest version.
- **Hansen loss tiles**: the URL pattern is confirmed.
- **`umd_tree_cover_loss_from_fires`**: confirmed (v1.13).
- **IGN WMTS**: URL templates added.

Owner decisions (spec §15):
- Thresholds 10/30/50.
- 3 confidence levels.
- Generic admin-level naming.
- Synthetic demo data.
- Warehouse published as a GitHub Release asset.
- MIT licence.
