---
name: web-bug-bounty
description: Automate web bug bounty hunting with full reconnaissance, systematic vulnerability testing across 16 categories, GIF PoC capture, and structured reporting. Use when the user asks to "start bug bounty", "test for vulnerabilities", "scan a target", "run security assessment", "pentest this scope", or provides a scope config file for security testing.
---

# Web Bug Bounty Hunter

Automated bug bounty pipeline: Recon -> Attack -> Report -> Loop. Operate as a 30-year veteran web security expert. Test systematically, document precisely, and exhaust all vulnerability categories across all discovered endpoints.

## Authorization Gate

<HARD-GATE>
Before ANY testing, confirm with the user:
1. The target is authorized for testing (bug bounty program, pentest engagement, or owned asset)
2. The scope config file path is provided
3. The user has logged into the target in Chrome (for authenticated testing)

Do NOT proceed without explicit confirmation of authorization.
</HARD-GATE>

## Invocation

User provides: path to a scope config file (JSON). See `examples/scope-config-example.json` for format.

Example: "Run bug bounty on scopes/hackerone-example.json"

If no scope file exists yet, create one interactively by asking:
1. Target URL(s)
2. In-scope domains/paths
3. Out-of-scope exclusions
4. Login URL (if auth needed)
5. Program notes

Save to `scopes/<target-name>.json`.

## Pipeline

Execute phases in order. Track progress across all phases.

### Phase 0: INIT

1. Read and validate the scope config JSON file
2. Run tool dependency check:
   ```bash
   bash skills/web-bug-bounty/scripts/install-tools.sh
   ```
   If critical tools fail to install, warn the user and list manual install steps.
3. Verify Chrome session:
   - Load `mcp__claude-in-chrome__tabs_context_mcp` via ToolSearch
   - Check current browser tabs
   - Navigate to the target's `login_url`
   - Verify the user is logged in (check for session cookies, dashboard content)
   - If not logged in, ask the user to log in manually and wait
4. Create output directories:
   ```bash
   mkdir -p reports/<scope-name>
   ```
5. Initialize progress tracker — a mental model of: endpoints (discovered in Phase 1) x 16 vulnerability categories. Start with zero endpoints.

### Phase 1: RECON

Read `references/recon.md` for detailed procedures.

Execute the 10-step recon pipeline:
1. Domain analysis
2. Subdomain enumeration (subfinder)
3. Live host detection (httpx)
4. Port scanning (nmap)
5. Directory/file discovery (ffuf)
6. Technology fingerprinting (Chrome + curl)
7. JS analysis & API endpoint mining (Chrome)
8. Interactive crawling (Chrome)
9. Parameter discovery (arjun)
10. Compile results to `recon-results.json`

**Output:** Print summary of discovered assets:
- N subdomains found
- N live hosts
- N endpoints discovered
- N forms found
- Key technologies identified
- Notable findings (exposed files, interesting paths)

### Phase 2: ATTACK

Read `references/attack-vectors.md` for detailed procedures per category.
Read `references/chrome-testing.md` for Chrome tool patterns.
Read `references/cli-tools.md` for CLI tool syntax.

Build the testing matrix from `recon-results.json` endpoints x 16 categories.

For each endpoint, for each applicable category:
1. Announce: "Testing [endpoint] for [category]"
2. Run Chrome-based tests (interactive payloads, DOM inspection, response analysis)
3. Run CLI-based tests (nuclei, sqlmap, ffuf, curl as appropriate)
4. Evaluate results:
   - If anomaly detected: investigate deeper with targeted Chrome testing
   - If vulnerability confirmed:
     a. Start GIF recording via `mcp__claude-in-chrome__gif_creator`
     b. Reproduce the vulnerability step-by-step (capture extra frames for smooth playback)
     c. Stop GIF recording, save to `reports/<scope>/`
     d. Record finding in `findings.json`
   - If clean: mark as tested, move to next
5. Update progress tracker

**Scope enforcement:** Before EVERY request, verify the URL is within `in_scope` and not in `out_of_scope`. Skip any URL that violates scope.

**Rate limiting:** Add 1-second delays between requests to avoid triggering WAF/rate limits. If a 429 response is received, back off for 30 seconds.

### Phase 3: REPORT

Read `references/report-template.md` for templates and formatting.

For each finding in `findings.json`:
1. Generate a per-vulnerability report using the template
2. Include the GIF PoC reference
3. Calculate CVSS 3.1 score with vector string
4. Write remediation recommendations
5. Save to `reports/<scope-name>/<category>-<date>-<NNN>.md`

### Phase 4: LOOP

1. Check progress tracker: how many endpoint x category combinations remain untested?
2. Print progress: "Coverage: X/Y combinations tested (Z%). Findings: N"
3. If untested combinations remain: return to Phase 2 with next batch
4. If all combinations tested:
   a. Generate summary report (`reports/<scope-name>/summary-<date>.md`)
   b. Print final results:
      - Total findings by severity
      - Coverage percentage
      - Path to summary report
   c. Pipeline complete

## Progress Reporting

At each category completion, print:
```
[PROGRESS] Category: XSS — Endpoints tested: 15/15 — Findings: 2
[PROGRESS] Overall: 45/240 combinations tested (18.75%) — Total findings: 3
```

## Error Handling

- If a CLI tool is not available and cannot be installed: skip CLI testing for affected categories, note in report
- If Chrome extension is unresponsive: warn user, continue with CLI-only testing
- If a target returns consistent 403/WAF blocks: note in report, try alternative paths, reduce request rate
- If scope config is invalid JSON: show error and ask user to fix

## Safety Rules

- NEVER test out-of-scope URLs — check EVERY URL against scope patterns before requesting
- NEVER send destructive requests (DELETE, DROP, data modification) unless scope config explicitly allows
- NEVER attempt denial of service or resource exhaustion
- Add delays between requests (minimum 1 second)
- All data stays local — never transmit findings to external services
- Announce each attack category before starting — user can say "skip" to bypass any category
