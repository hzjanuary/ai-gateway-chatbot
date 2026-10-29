# Actual-image Python license inventory

2026-10-29 revalidation: local existing images and four new remote image builds
retain the same 17/44 distribution text inventories and exact raw Trivy license
matches as the baseline. Raw Trivy counts are 684 headless / 1718 UI, including
the existing UI CRITICAL license-category WTFPL match in PyArrow's bundled
LICENSE.txt. These classifications remain unsuppressed; distribution metadata
success is not blanket approval of bundled/OS license obligations. See
[new remote evidence](evidence/remote-ci-4bde829.json). No image is published.

Image source: `46744d5aed5a797701c0bea00705664f0f229a13`. Inventory was executed inside each release image with networking disabled. Headless has 17 distributions; optional UI has 44. Full license texts and raw metadata are preserved under `.local/verification/accepted-{headless,ui}-security/image-licenses.json`, with hashes in [evidence summary](evidence/summary.json). OS packages and corresponding source-package versions are retained in `os-packages.json` and the image CycloneDX SBOM; OS redistribution obligations still require review before image publication.

| Package | Version | Metadata license | Actual image text |
| --- | --- | --- | --- |
| altair | 6.3.0 | License text in inventory | present |
| annotated-doc | 0.0.5 | MIT | present |
| annotated-types | 0.8.0 | MIT | present |
| anyio | 4.15.1 | MIT | present |
| attrs | 26.1.0 | MIT | present |
| certifi | 2026.10.23 | MPL-2.0 | present |
| charset-normalizer | 3.5.2 | MIT | present |
| click | 8.5.0 | BSD-3-Clause | present |
| fastapi | 0.162.0 | MIT | present |
| h11 | 0.16.0 | MIT | present |
| httpcore | 1.0.9 | BSD-3-Clause | present |
| httpx | 0.28.1 | BSD-3-Clause | present |
| idna | 3.20 | BSD-3-Clause | present |
| itsdangerous | 2.2.0 | BSD License | present |
| Jinja2 | 3.1.6 | BSD License | present |
| jsonschema | 4.26.0 | MIT | present |
| jsonschema-specifications | 2025.9.1 | MIT | present |
| MarkupSafe | 3.0.4 | BSD-3-Clause | present |
| narwhals | 2.28.0 | MIT | present |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | present |
| opentelemetry-api | 1.45.1 | Apache-2.0 | present |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | present |
| pandas | 3.1.0 | BSD-3-Clause | present |
| pillow | 13.0.0 | MIT-CMU | present |
| protobuf | 7.36.2 | 3-Clause BSD License | present |
| pyarrow | 26.0.0 | Apache-2.0 | present |
| pydantic | 2.14.1 | MIT | present |
| pydantic_core | 2.50.1 | MIT | present |
| pydeck | 0.9.3 | Apache License 2.0 | present |
| python-dateutil | 3.0.0 | Dual License | present |
| python-multipart | 0.0.32 | Apache-2.0 | present |
| referencing | 0.37.0 | MIT | present |
| requests | 2.34.2 | Apache-2.0 | present |
| rpds-py | 2026.9.1 | MIT | present |
| six | 1.17.0 | MIT | present |
| starlette | 1.10.0 | BSD-3-Clause | present |
| streamlit | 1.66.1 | Apache-2.0 | present |
| typing-inspection | 0.4.4 | MIT | present |
| typing_extensions | 4.16.0 | PSF-2.0 | present |
| tzdata | 2026.6 | Apache-2.0 | present |
| urllib3 | 2.8.0 | MIT | present |
| uvicorn | 0.54.0 | BSD-3-Clause | present |
| watchdog | 6.0.0 | Apache-2.0 | present |
| websockets | 17.3 | BSD-3-Clause | present |

Streamlit wheel omission is repaired with the exact official 1.66.1 Apache-2.0 text; [manifest](../../licenses/manifest.json) records its immutable checksum/source. PSF-2.0 and dual Apache/BSD classifier metadata are recognized explicitly. No missing or unknown Python license was waived. This inventory does not grant permission to publish the OS image with a failed vulnerability gate.
