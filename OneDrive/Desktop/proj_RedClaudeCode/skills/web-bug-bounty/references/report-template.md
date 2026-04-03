# Phase 3: Report Generation

Guide for generating vulnerability reports and summary documents.

## Per-Vulnerability Report

For each confirmed finding, create a report at:
`reports/<scope-name>/<vuln-category>-<date>.md`

If multiple findings of same category exist, append a number:
`reports/<scope-name>/sqli-2026-04-02-001.md`

### Default Template

```markdown
# [Vulnerability Title]

## Summary

| Field | Value |
|-------|-------|
| **Type** | [e.g., Reflected XSS, Union-based SQL Injection] |
| **Severity** | [Critical / High / Medium / Low / Informational] |
| **CVSS 3.1** | [Score, e.g., 9.8] |
| **URL** | `[Affected endpoint URL]` |
| **Parameter** | `[Affected parameter name]` |
| **Method** | [GET / POST / PUT / etc.] |

## Description

[2-3 sentences describing the vulnerability, what it is, and where it exists. Written from the perspective of a security researcher explaining to a developer.]

## Steps to Reproduce

1. [Step 1]
2. [Step 2]
3. [Step 3]

**Request:**
```http
[Full HTTP request that triggers the vulnerability]
```

**Response (relevant portion):**
```http
[Response showing the vulnerability — error message, reflected payload, leaked data, etc.]
```

## Proof of Concept

![PoC Recording](./[filename]-poc.gif)

[1-2 sentence caption describing what the GIF shows]

## Impact

[What can an attacker achieve by exploiting this vulnerability? Be specific:]
- [Data access: what data? whose data?]
- [Account takeover: how?]
- [Code execution: what context?]
- [Financial impact: what operations?]

## CVSS 3.1 Vector

```
CVSS:3.1/AV:[N/A/L/P]/AC:[L/H]/PR:[N/L/H]/UI:[N/R]/S:[U/C]/C:[N/L/H]/I:[N/L/H]/A:[N/L/H]
```

[Brief justification for each metric choice]

## Remediation

**Recommended fix:**
[Specific, actionable remediation steps]

**Example secure code:**
```[language]
[Code snippet showing the fix]
```

**References:**
- [Link to relevant OWASP page]
- [Link to relevant CWE]
```

### CVSS Scoring Guide

Use these baselines, adjust per context:

| Severity | CVSS Range | Examples |
|----------|-----------|----------|
| Critical | 9.0 - 10.0 | RCE, auth bypass on admin, unauthenticated SQLi with data access |
| High | 7.0 - 8.9 | Stored XSS on widely used page, IDOR leaking PII, SSRF to internal services |
| Medium | 4.0 - 6.9 | Reflected XSS requiring interaction, CSRF on non-critical action, open redirect |
| Low | 0.1 - 3.9 | Information disclosure (version numbers), missing security headers |
| Informational | 0.0 | Best practice recommendations, no direct exploitability |

## Summary Report

After all testing is complete, generate a summary at:
`reports/<scope-name>/summary-<date>.md`

### Summary Template

```markdown
# Bug Bounty Report Summary — [Program Name]

**Target:** [Base URL]
**Date:** [YYYY-MM-DD]
**Tester:** [Name/Handle]

## Executive Summary

[2-3 sentences: scope tested, key findings, overall security posture]

## Statistics

| Metric | Value |
|--------|-------|
| Endpoints Discovered | [N] |
| Endpoints Tested | [N] |
| Vulnerability Categories Tested | 16 / 16 |
| Total Findings | [N] |
| Critical | [N] |
| High | [N] |
| Medium | [N] |
| Low | [N] |
| Informational | [N] |

## Findings

| # | Title | Severity | CVSS | Endpoint | Report |
|---|-------|----------|------|----------|--------|
| 1 | [Title] | Critical | 9.8 | `[URL]` | [Link](./sqli-2026-04-02-001.md) |
| 2 | [Title] | High | 7.5 | `[URL]` | [Link](./xss-2026-04-02-001.md) |

## Coverage Matrix

| Endpoint | SQLi | XSS | SSRF | IDOR | Auth | LFI | Info | JWT | CORS | CSRF | Redir | CRLF | Host | Logic | Cache | Race |
|----------|------|-----|------|------|------|-----|------|-----|------|------|-------|------|------|-------|-------|------|
| /api/users | VULN | clean | N/A | VULN | clean | clean | clean | clean | clean | N/A | N/A | clean | clean | clean | N/A | clean |
| /search | clean | VULN | N/A | N/A | N/A | clean | clean | N/A | clean | clean | clean | clean | clean | N/A | clean | N/A |

Legend: `VULN` = finding, `clean` = tested no issue, `N/A` = not applicable

## Recommendations

[Prioritized list of remediation actions]
1. [Most critical fix first]
2. [Second most critical]
3. [...]
```

## Custom Templates

If `custom_template_path` is set in scope config, read that file and use its structure instead of the default template. The custom template must contain at minimum: Title, Description, Steps to Reproduce, Impact, and Remediation sections.

## File Naming Convention

- Report files: `<category>-<date>-<NNN>.md` (e.g., `sqli-2026-04-02-001.md`)
- GIF files: `<category>-<date>-<NNN>-poc.gif` (e.g., `sqli-2026-04-02-001-poc.gif`)
- Summary: `summary-<date>.md`
- All files go in `reports/<scope-name>/` directory
