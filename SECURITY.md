# Security policy

## Supported version

Security fixes are applied to the latest branch under active development. This
project has not declared a long-term-support release line.

## Report a vulnerability

Do not open a public issue for a suspected vulnerability involving arbitrary
file access, command execution, unsafe HTML, conversion of untrusted documents,
or dependency compromise.

Use GitHub's private vulnerability reporting for this repository when
available. Otherwise, contact the repository owner through the verified
PlatanoGames profile and include:

- affected commit or version;
- reproduction steps;
- expected security boundary and observed behavior;
- impact assessment;
- any proposed mitigation.

Avoid sharing real confidential documents. Use a minimal synthetic sample.

## Security boundary

DocsConverter invokes local conversion tooling and processes user-selected
files. Treat untrusted Markdown, templates, filters, and Pandoc extensions as
potentially unsafe, and review generated output before publishing it.
