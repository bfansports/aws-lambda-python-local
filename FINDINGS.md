# AI Audit: aws-lambda-python-local

**Date:** 2026-02-17
**Auditor:** Backend Developer Agent (Claude Opus 4.6)
**Repo:** bfansports/aws-lambda-python-local
**Branch:** master (commit 4b753f1)
**Focus:** Execution safety, sandboxing, dependency management, Python version compatibility

---

## Critical

### C1 — Arbitrary Code Execution via `importlib.import_module` (run.py:36)

**File:** `run.py`
**Line:** 36

```python
module = importlib.import_module('src.{name}.index'.format(name=args.name))
```

The `name` argument is taken directly from CLI input with no validation or sanitization. While this is a local dev tool (not a server), the pattern allows loading any Python module on `PYTHONPATH` by crafting the name argument (e.g., `../../malicious_module`). The `src.{name}.index` pattern provides some path scoping but does not prevent directory traversal via Python module names.

**Risk:** A malicious event file or CI configuration could exploit this to execute arbitrary code.
**Recommendation:** Validate `args.name` against a whitelist of actual function directories:
```python
import os
valid_funcs = [d for d in os.listdir('src') if os.path.isdir(os.path.join('src', d)) and d != '__pycache__']
if args.name not in valid_funcs:
    sys.exit(f"Unknown function: {args.name}. Available: {', '.join(valid_funcs)}")
```

### C2 — Secrets Bundled in Deployment ZIP (Makefile:111-115, 128-130)

**File:** `Makefile`
**Lines:** 111-115, 128-130

The `.env` file is downloaded from S3, converted to `lib/env.py`, and then **zipped into every Lambda deployment package**. This means secrets (API keys, account IDs, Cognito pool IDs) are permanently embedded in the ZIP artifact stored in S3.

```makefile
.env:
    aws s3 cp s3://sportarchive-${ENV}-code/${ENV}_creds ./lib/env.py
    cp ./lib/env.py .env
```

```makefile
dist/%.zip: src/%/* build/setup.cfg $(wildcard lib/**/*) .env
    ...
    zip -r -q $@ lib    # <-- lib/env.py with secrets included
```

**Risk:** Secrets persist in S3 ZIP artifacts, Lambda package history, and local build artifacts. Anyone with S3 read access to the code bucket gets all secrets.
**Recommendation:** Migrate to AWS Secrets Manager or SSM Parameter Store. Lambda functions should fetch secrets at runtime, not bundle them.

### C3 — Hardcoded AWS Account Info and S3 Buckets (Makefile, multiple lines)

**File:** `Makefile`
**Lines:** 88, 93, 104, 106-107, 129

The S3 bucket name `sportarchive-${ENV}-code` and the IAM role `arn:aws:iam::${AWS_ACCOUNT}:role/lambda_orchestrate_role` are hardcoded. The role ARN has a malformed format (double colon `::` with no account ID between them — it relies on `${AWS_ACCOUNT}` env var which is never set by the Makefile itself).

```makefile
aws s3 cp $< s3://sportarchive-${ENV}-code/lambda/$(<F)
--role arn:aws:iam::${AWS_ACCOUNT}:role/lambda_orchestrate_role
```

**Risk:** Accidental deployment to wrong environment; credentials confusion; the old "sportarchive" naming suggests this may point to a decommissioned bucket.
**Recommendation:** Move to environment variables or a config file (`config.mk` or `.env`-based). Validate required vars before running deploy targets.

---

## High

### H1 — `hmac.new` Typo in AWS Signature V4 (lib/apiconnect.py:58, 100)

**File:** `lib/apiconnect.py`
**Lines:** 58, 100

```python
def sign(self, key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
```

Python's `hmac` module uses `hmac.new()`, which is correct. However, this is fragile because `hmac.new` is actually the constructor — the canonical name is `hmac.new`. While this works, line 100 also uses `hmac.new` directly:

```python
signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()
```

This is functional but the manual SigV4 implementation is error-prone and should be replaced with `botocore.auth.SigV4Auth` or `requests-aws4auth`.

**Risk:** Manual signature implementation is brittle and hard to maintain. Any subtle bug causes silent auth failures.
**Recommendation:** Replace manual SigV4 with `botocore.auth.SigV4Auth` or the `aws-requests-auth` package.

### H2 — Hardcoded Region `us-east-1` (lib/apiconnect.py:75)

**File:** `lib/apiconnect.py`
**Line:** 75

```python
self.region = 'us-east-1'
```

**Risk:** Cannot test against APIs in other regions without code changes.
**Recommendation:** Read from `env.py` or `AWS_DEFAULT_REGION` environment variable.

### H3 — Runtime Python 3.8 Is EOL (Makefile:92, scripts/lambda_configuration_update.sh:7)

**File:** `Makefile` line 92, `scripts/lambda_configuration_update.sh` line 7

```makefile
--runtime python3.8
```

```bash
OUT=`aws lambda update-function-configuration \
      --function-name ${FUNC} \
      --runtime python3.8`
```

Python 3.8 reached end-of-life in October 2024. AWS Lambda deprecated Python 3.8 runtime. Functions using it cannot be created (only updated), and will eventually lose update support.

**Risk:** New function creation will fail. Existing functions face forced runtime upgrade.
**Recommendation:** Update to `python3.12` (current LTS on Lambda) in both files.

### H4 — No Execution Sandboxing for Local Runs

**File:** `run.py`

The local runner executes Lambda handler code with the same permissions as the developer's shell. There is no:
- Resource limiting (memory, CPU, time)
- Network isolation
- Filesystem sandboxing
- Environment variable isolation

`MockContext.get_remaining_time_in_millis()` returns `float('inf')` (line 43-44 of MockContext.py), meaning a function that checks timeout will never terminate.

**Risk:** Local testing behavior diverges from Lambda's constrained environment. Functions may pass locally but fail in production due to timeout, memory, or permission differences.
**Recommendation:** At minimum, implement a configurable timeout that matches Lambda's timeout setting (default 10s per Makefile line 97). Consider Docker-based local execution (SAM CLI or similar).

### H5 — Open Dependabot PR for Security Fix (requests 2.31.0 -> 2.32.2)

**File:** `requirements.txt`

PR #6 has been open since November 2024 (15+ months). It bumps `requests` from 2.31.0 to 2.32.2, which includes CVE-2024-35195 (TLS verification bypass when `verify=False` is set on first request in a Session).

**Risk:** Known security vulnerability in a direct dependency.
**Recommendation:** Merge PR #6 immediately.

---

## Medium

### M1 — Test File References Wrong Module (tests/testExampleFunc.py:9)

**File:** `tests/testExampleFunc.py`
**Line:** 9

```python
def run_func(**keyword_args):
    return src.assets.index.handler(
        keyword_args['event'],
        keyword_args['context'])
```

The function calls `src.assets.index.handler` but the test imports `src.example_func.index` (line 6). There is no `src/assets/` directory in the repo. The test will always fail with `NameError: name 'src' is not defined` (since `src.assets` was never imported) or `ModuleNotFoundError`.

**Risk:** Tests provide false confidence — they don't actually validate anything.
**Recommendation:** Fix to `src.example_func.index.handler(...)` and verify the test actually runs.

### M2 — MockContext Makes Live AWS Calls (tests/MockContext.py:31-36, 66-71)

**File:** `tests/MockContext.py`
**Lines:** 31-36, 66-71

```python
res = boto3.client('cognito-identity').get_id(
    AccountId=env.AWS_ACCOUNT_ID,
    IdentityPoolId=env.IDENTITY_POOL
)
```

Both `MockContext` and `_add_cognito_id` make real AWS Cognito API calls during test setup. Unit tests should not require live AWS credentials or network access.

**Risk:** Tests fail without AWS credentials configured. Tests are not reproducible in CI without AWS access. Flaky due to network dependency.
**Recommendation:** Use `moto` library or `unittest.mock` to stub Cognito calls. Provide a `MockContextUnitTest` that works fully offline (one exists but still calls Cognito in `_add_cognito_id`).

### M3 — `lib/common.py` Imports `lib.env` at Module Level (line 10)

**File:** `lib/common.py`
**Line:** 10

```python
from lib import env
```

`lib/env.py` is generated from S3 download and is gitignored. Any import of `lib.common` will fail with `ImportError` if `env.py` doesn't exist. This affects `run.py`, `connect.py`, and all tests — none can even import without first running `make .env`.

**Risk:** Confusing error for new developers. `pip install -r requirements.txt` is insufficient to run anything.
**Recommendation:** Guard the import with try/except or move env-dependent functions to a separate module. At minimum, document the dependency prominently.

### M4 — Identity Cache File Written with No Permissions Check (lib/common.py:60-62)

**File:** `lib/common.py`
**Lines:** 60-62

```python
def put_identity(IdentityId):
    myfile = open('.identity_'+env.CONFIG_MODE, 'w')
    myfile.write(IdentityId)
    myfile.close()
```

Cognito Identity IDs are written to local files (`.identity_DEV`, `.identity_PROD`) with default permissions (typically 0644). These files contain AWS identity information.

**Risk:** Identity tokens readable by other users on shared machines.
**Recommendation:** Use `os.open()` with explicit permissions (0600) or write to a user-specific temp directory. Also use `with` statement for proper file handling.

### M5 — Shell Injection Risk in Makefile `api` Target (Makefile:57-74)

**File:** `Makefile`
**Lines:** 57-74

```makefile
$(eval ORCHESTRATE_AUTH = 'Basic $(shell echo -n "${ORCHESTRATE_KEY}:" | base64)')
sed -i "s/%ORCH_CREDS%/${ORCHESTRATE_AUTH}/g" ${DST_FILE}
sed -i "s/%AWS_ACCOUNT%/${AWS_ACCOUNT}/g" ${DST_FILE}
```

`sed -i` with unescaped variable substitution. If `ORCHESTRATE_KEY` or `AWS_ACCOUNT` contain sed metacharacters, the command will fail or behave unexpectedly. Also, `sed -i` without backup extension is GNU-specific and fails on macOS BSD sed.

**Risk:** Build failure on macOS; potential for unexpected substitution if env vars contain special characters.
**Recommendation:** Use `sed -i '' ...` for macOS compatibility or use `envsubst` instead of `sed`.

### M6 — `pip install -t` Without `--upgrade` or Version Pinning (Makefile:120)

**File:** `Makefile`
**Line:** 120

```makefile
pip install -r $^ -t $(@D)
```

Dependencies are installed into `build/` without `--upgrade` flag. Only `boto3` and `requests` are pinned. Transitive dependencies are not locked (no `requirements.lock` or `pip freeze` output).

**Risk:** Non-reproducible builds; different developers get different transitive dependency versions.
**Recommendation:** Add a lock file (`pip-compile` from `pip-tools`) and pin all transitive dependencies.

### M7 — GitHub Actions Workflow References Non-Existent `develop` Branch

**File:** `.github/workflows/github-backup.yml`
**Line:** 5

```yaml
on:
  push:
    branches:
      - develop
```

The repo's default branch is `master`, not `develop`. This workflow never triggers.

**Risk:** S3 backups are not running.
**Recommendation:** Change to `master` or remove if backups are handled elsewhere.

---

## Low

### L1 — Inconsistent Indentation in Test File (tests/testExampleFunc.py)

**File:** `tests/testExampleFunc.py`

Mixes 4-space and 8+ space indentation. Class body uses ~12 spaces. This is valid Python but hurts readability and suggests copy-paste errors.

**Recommendation:** Reformat to standard 4-space indentation.

### L2 — Unused Imports Across Multiple Files

- `lib/common.py` — `string` (line 8) is imported but never used
- `lib/common.py` — `requests` (line 7) is imported but never used  
- `lib/common.py` — `HTTPError` from `urllib.error` (line 9) is imported but never used
- `tests/MockContext.py` — `functools` (line 1), `uuid` (line 3), `copy` (line 5) are unused
- `tests/testExampleFunc.py` — `uuid` (line 2), `copy` (line 3) are unused
- `run.py` — `lib` (line 11) is imported but never used

**Recommendation:** Remove unused imports. Consider adding `flake8` or `ruff` to CI.

### L3 — Semicolons in Python (run.py:38)

```python
event = json.loads(event);
```

Trailing semicolon is a style issue (likely a Java/JS habit). Harmless but non-Pythonic.

### L4 — `connect.py` Description Says "Run a Lambda function locally" (line 11)

**File:** `connect.py`
**Line:** 11

```python
parser = argparse.ArgumentParser(description='Run a Lambda function locally.')
```

The description is copy-pasted from `run.py`. Should say "Connect to API Gateway endpoint."

### L5 — Missing HTTP Methods in `callApi` (lib/apiconnect.py:116-123)

Only GET, POST, PUT, DELETE are handled. PATCH is mentioned in the Makefile help text but not implemented. HEAD, OPTIONS are also missing.

**Recommendation:** Add PATCH support or use `requests.request(method, ...)` for generic method support.

### L6 — `noauth` Argument Logic Inverted (connect.py:28, lib/apiconnect.py:28)

The `--noauth` flag's help says "Use a new identity even if .identity file exists" but the code checks `if (noauth == 0 and self.IdentityId is False)`. When `--noauth` is provided (noauth=1), the cached identity check is skipped entirely and the code falls through to use `self.IdentityId` which would be the cached value from `common.get_identity()` — the opposite of the intended behavior.

**Risk:** The `--noauth` flag does not work as documented.
**Recommendation:** Review and fix the conditional logic.

### L7 — `aws-apigateway-importer` Submodule Is Deprecated

**File:** `.gitmodules`

The `aws-apigateway-importer` tool from awslabs was archived years ago. AWS CLI now supports `aws apigateway put-rest-api` and `import-rest-api` natively.

**Recommendation:** Remove the submodule; use `aws apigateway import-rest-api` or migrate to SAM/CDK.

---

## Agent Skill Improvements

Recommendations for improving the CLAUDE.md in this repo:

1. **Add architecture diagram** — The relationship between run.py, connect.py, Makefile, lib/, and src/ is non-obvious. A text diagram helps agents navigate.
2. **Document the env.py generation flow** — The S3 -> .env -> lib/env.py -> ZIP chain is the most confusing part of the codebase. Agents waste tokens rediscovering it.
3. **List all Makefile targets** — Agents need to know available commands without parsing Makefile.
4. **Mark the repo as legacy/inactive** — If this framework has been superseded by SAM or CDK, say so explicitly. Agents should not suggest building on top of it.
5. **Add security section** — Document the secrets-in-ZIP pattern so agents flag it immediately.
6. **Add test running prerequisites** — Document that `make .env` (requires AWS creds) is needed before anything works.

---

## Positive Observations

1. **Clean function isolation pattern** — One function per `src/<name>/` directory with standardized `index.py:handler` entry point is a good convention that predates SAM's template.yaml approach.
2. **Makefile automation is comprehensive** — Create, deploy, test, connect, and API management all in one file. For its era (2015-2016), this was well-designed.
3. **Cognito integration for local testing** — The ability to get real temporary credentials and test authenticated API endpoints locally is valuable and often missing from Lambda frameworks.
4. **Identity caching** — The `.identity_*` file caching avoids unnecessary Cognito calls during development iteration.
5. **Shared lib pattern** — The `lib/` directory with automatic inclusion in ZIPs was a practical solution before Lambda Layers existed.
6. **Existing CLAUDE.md** — The repo already has a well-structured CLAUDE.md with the right sections, Ask tags for unknown info, and accurate gotchas documentation.
7. **Gitignore is thorough** — Properly excludes `.env`, `.identity_*`, `lib/env.py`, build artifacts, and Python cache files.
