# Guides

Reference and methodology guides — companions to the design docs (RFCs/ADRs/concept package). Where the design docs argue *what* and *why*, guides explain *how* a topic is approached in practice.

## Available guides

- [Standardized testing](standardized-testing.md) — companion to RFC-019. Industry methodology for reference-image validation, the Calibrite ColorChecker reference values, Delta E 2000 interpretation, and synthetic-fixture generation.

## Adding a guide

A guide is appropriate when:

- A topic spans multiple design docs and a single landing reference helps readers connect them.
- An external standard, methodology, or tooling reference is cited often enough to deserve a curated summary.
- A how-to is non-trivial and benefits from being a stable, linkable artifact rather than scattered comments.

Conventions:
- One topic per file. Slug-cased filename.
- Lead with a one-line summary identifying the design doc this guide companions (if any).
- Cross-link from the originating RFC/ADR.
- Treat external references as canonical — link out, don't restate.
