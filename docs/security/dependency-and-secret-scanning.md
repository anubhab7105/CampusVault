# Dependency and secret scanning

CampusVault runs automated dependency and secret scans on pull requests and branch pushes through GitHub Actions.

## Required checks

- **Python:** `pip-audit --strict` checks the backend runtime, test, and development requirements. Any reported vulnerable installed dependency fails the job.
- **Frontend:** `npm audit --audit-level=high` fails for high or critical npm advisories. The job also uploads the full npm audit JSON report so moderate and low findings remain visible for review.
- **Secrets:** Gitleaks scans the checked-out repository history. Treat any detected credential as potentially exposed.
- **Pull request dependency changes:** GitHub's dependency review action evaluates dependency changes on pull requests and is not controlled by a repository variable.

The checks are not conditional on optional repository variables. A scanner setup or execution failure should be investigated and fixed rather than bypassed.

## Triage and suppressions

1. Open the failing workflow job and inspect the package, advisory or Gitleaks finding and the affected file/commit.
2. For dependency findings, upgrade to a patched compatible version and update the relevant lock/requirements files. If a fix is not available, document the exact package, advisory identifier, affected version, impact, mitigation, owner and review date in an issue. Do not silently lower the audit threshold or hide the report.
3. For a likely secret false positive, verify the value is not a real credential. Use a narrowly scoped Gitleaks allowlist only for a confirmed false positive, with a comment explaining why it is safe. Never allowlist an entire directory or broad rule to make a scan pass.
4. Keep any accepted risk explicit, time-bounded and reviewed. Re-run the workflow after updating the dependency, configuration or narrowly scoped suppression.

## Credential exposure response

If a live key, token, password, cookie or private key is detected:

1. Revoke or rotate it immediately with the issuing provider; remove it from active configuration and replace it with a secret-manager/environment variable.
2. Review provider audit logs and access history for suspicious use.
3. Remove the credential from tracked files and, where necessary, coordinate history cleanup. Deleting it in a later commit does not make the old value safe.
4. Record the incident and rotation in a private channel; do not paste the secret into issues or workflow logs.

## Local commands

From the repository root:

```bash
python -m pip install pip-audit
python -m pip install -r backend/requirements/base.txt -r backend/requirements/test.txt -r backend/requirements/dev.txt
pip-audit --strict

cd frontend
npm ci
npm audit --audit-level=high
npm audit --json > npm-audit-report.json
```

For local secret scanning, install Gitleaks using its official installation instructions and run `gitleaks git --redact` from the repository root.
