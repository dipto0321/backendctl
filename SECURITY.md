# Security Policy

## Supported versions

`backendctl` is in active early development. Security fixes are applied to the
latest released version on PyPI.

| Version | Supported |
|---------|-----------|
| latest `0.3.x` | ✅ |
| older | ❌ |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
discussions, or pull requests.**

Instead, report privately using GitHub's
[private vulnerability reporting](https://github.com/dipto0321/backendctl/security/advisories/new).
If you cannot use that, email **diptokmk47@gmail.com** with the details.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce or a proof of concept.
- The affected version (`backendctl --version`) and environment.

You can expect an acknowledgement within **5 business days**. We will keep you
informed of progress and coordinate a disclosure timeline once a fix is ready.

## Scope notes

`backendctl` generates project scaffolding. Two areas deserve special attention
when reporting:

- **The CLI itself** — e.g. unsafe file writes, command injection in the
  generator, or leaking secrets.
- **Generated output** — insecure defaults in the code we scaffold (auth,
  secret handling, dependency versions). These are in scope; please specify
  which framework template is affected.

Generated `.env` files contain locally generated secrets and are git-ignored by
the scaffold — never commit them.
