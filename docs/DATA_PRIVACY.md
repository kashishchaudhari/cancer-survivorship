# Confidential data and repository policy

The user has identified the dataset as confidential and permission-restricted. Treat raw inputs and derived outputs as restricted; aggregate-only does not mean publicly shareable.

## Local storage

Keep original sources in their existing approved location. Do not copy them into Git. `data/local`, `outputs`, `dashboard/data`, runtime files, real-data workbooks, and result reports are ignored. The original source files are preserved.

The current localhost preview contains confidential results. It binds to 127.0.0.1 and is not a public hosting service. Data-backed screenshots also remain local. Cloud upload, public posting and hosting require permission for the specific data and destination.

## GitHub

The repository must contain code, methodology and invented-fixture generation only. CI tests synthetic fixtures; it uploads no artifacts and deploys no Pages site. A private repository does not itself authorize restricted-data storage. Do not upload the actual ZIP even to a private repository without permission.

The existing local Git history contains previously committed derived files. `.gitignore` and removing current tracking do **not** remove historical copies. Do not push that history. A fresh code-only export can be initialized as a new repository after checking every included file. Preserve the original local repository and source files; do not rewrite history silently.

`uv run python scripts/check_repository_privacy.py` inspects current tracked paths only. It is not a certification of historical commits, remote visibility or all possible sensitive content. No remote is currently configured in the inspected checkout; that does not establish what may exist in other repositories.

## Publication options

- Public portfolio: code and explicitly synthetic demonstrations.
- Confidential research: authorized local environment, or an institution-approved access-controlled platform with the required permission.
- Actual findings: share only the permitted report/fields with the approved recipients after reviewing the data-use conditions.

GitHub Pages is a website publication mechanism and is not enabled for this confidential research dashboard. [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).
