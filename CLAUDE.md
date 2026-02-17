# aws-lambda-python-local

## What This Is

A Python development framework for writing, testing, and deploying AWS Lambda functions. Provides local execution environment that simulates Lambda's `event` and `context` objects, Cognito integration for testing authenticated APIs, API Gateway management via Swagger, and Makefile-driven deployment workflow.

**Status:** Legacy framework (created ~2015). Likely superseded by AWS SAM CLI or CDK for new Lambda development. Evaluate before building new functionality on top of it.

**Use case**: Rapid Lambda function development with local testing before deploying to AWS.

## Architecture

```
                  +------------------+
                  |    Makefile      |  (orchestrator — build, test, deploy, connect)
                  +--------+---------+
                           |
          +----------------+----------------+
          |                |                |
    +-----v-----+   +------v------+  +------v------+
    |  run.py   |   | connect.py  |  |  dist/*.zip |
    | (local    |   | (API test   |  | (deploy to  |
    |  runner)  |   |  client)    |  |  Lambda)    |
    +-----+-----+   +------+------+  +------+------+
          |                |                |
    +-----v-----+   +------v------+         |
    | MockContext|   |apiconnect.py|        |
    | (Lambda   |   | (SigV4 +    |        |
    |  context) |   |  Cognito)   |        |
    +-----+-----+   +------+------+        |
          |                |                |
    +-----v----------------v----------------v-----+
    |              lib/                            |
    |  common.py  — shared utilities               |
    |  env.py     — secrets (generated from S3)    |
    +----------------------------------------------+
          |
    +-----v-----+
    |   src/    |   one subdirectory per Lambda function
    |  <func>/  |   each has index.py with handler(event, context)
    +-----------+
```

### Data Flow: Secrets (env.py generation)

```
S3 bucket (sportarchive-${ENV}-code)
  └── ${ENV}_creds                    (key-value file)
        │
        ▼  `make .env`  (aws s3 cp)
      ./lib/env.py                    (Python module with variables)
        │
        ├── imported by lib/common.py, tests/MockContext.py, lib/apiconnect.py
        └── bundled into every dist/*.zip  ⚠ SECURITY: secrets in artifact
```

**WARNING:** Secrets are bundled into Lambda ZIP packages. This is a known security issue (see FINDINGS.md C2). For new functions, use AWS Secrets Manager or SSM Parameter Store instead.

## Tech Stack

- **Language**: Python 3.x (code uses Python 3 syntax like `http.client`, `urllib.error`)
- **Lambda Runtime**: python3.8 (hardcoded in Makefile — **EOL, upgrade to python3.12**)
- **AWS Services**: Lambda, API Gateway, Cognito, S3
- **Tools**:
  - `aws-cli` 1.9+ — AWS resource management
  - `aws-apigateway-importer` — Swagger-based API deployment (Git submodule, **deprecated**)
  - `pip` 6+ — Python package management
- **Testing**: `unittest` module (tests require live AWS credentials for Cognito)
- **Build**: `Makefile` — all operations (build, test, deploy, run)

## Quick Start

```bash
# 1. Setup AWS credentials
aws configure  # Set up AWS credentials

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate env.py from S3 (REQUIRED before anything works)
make .env              # uses DEV by default
make .env ENV=prod     # for production

# 4. Create a new Lambda function
#    - Create src/<function-name>/ directory
#    - Add src/<function-name>/index.py with handler(event, context)
#    - Add src/<function-name>/__init__.py

# 5. Run locally
make run/<function> EVENT=events/test.json

# 6. Run unit tests
make test
make test/<specific-test>

# 7. Create function in AWS Lambda (first time)
make create/<function> DESC='My function description'

# 8. Deploy (update existing function)
make deploy/<function>
make deploy/<function> ENV=prod

# 9. Test API Gateway endpoint with Cognito auth
make connect ENDPOINT=/my_endpoint METHOD=GET QUERY="param=value"
```

**Prerequisites that trip up new developers:**
- `make .env` must run before `run`, `test`, `connect`, `create`, or `deploy` — it downloads secrets from S3
- AWS credentials must be configured with access to the S3 code bucket
- If `env.py` is missing, ALL imports fail (lib/common.py imports it at module level)

## Project Structure

```
.
├── src/                  Lambda function source code
│   ├── <function>/
│   │   ├── __init__.py
│   │   └── index.py      handler(event, context) entry point
│   └── example_func/     Example function for reference
├── lib/                  Shared libraries (copied into every ZIP)
│   ├── __init__.py
│   ├── common.py         Utilities: payload parsing, identity caching, error class
│   ├── apiconnect.py     Cognito auth + SigV4 signed API requests
│   └── env.py            ⚠ GENERATED — secrets from S3 (gitignored)
├── tests/                Unit tests
│   ├── MockContext.py    Lambda context simulator (makes live Cognito calls!)
│   ├── test*.py          Test files (auto-discovered by unittest)
│   └── data/             Test event JSON files
├── swagger/              API Gateway Swagger YAML definitions
├── scripts/              Utility scripts (runtime update)
├── run.py                Local Lambda executor
├── connect.py            API Gateway + Cognito test client
├── Makefile              Build/test/deploy automation
├── requirements.txt      Python deps (boto3, requests)
└── .env                  ⚠ GENERATED — local copy of env.py (gitignored)
```

## Dependencies

**External:**
- AWS Lambda — function execution environment
- AWS API Gateway — HTTP API layer
- AWS Cognito — authentication and temporary credentials
- AWS S3 — function code storage (ZIP files uploaded to S3 before Lambda update)

**Internal:**
- `lib/` directory — shared code copied into each function's ZIP
- `lib/env.py` — environment variables and secrets (downloaded from S3, gitignored)

**Python packages (requirements.txt):**
- `boto3==1.12.8` — AWS SDK (very outdated — current is 1.35+)
- `requests==2.31.0` — HTTP client (has open CVE, PR #6 pending for 2.32.2)

<!-- Ask: What S3 bucket is used for Lambda function storage? Is it still sportarchive-*? -->
<!-- Ask: Is this framework still in active use, or has it been replaced by SAM/CDK? -->
<!-- Ask: Are there any active Lambda functions still deployed using this framework? -->

## Makefile Targets Reference

| Target | Description | Example |
|--------|-------------|---------|
| `make help` | Show all available commands | `make` |
| `make run/<func>` | Run function locally | `make run/example_func EVENT=test.json VERBOSE=1` |
| `make test` | Run all unit tests | `make test VERBOSE=1` |
| `make test/<name>` | Run specific test | `make test/ExampleFunc` |
| `make create/<func>` | Create new Lambda function in AWS | `make create/signin DESC='User signin'` |
| `make deploy/<func>` | Deploy function update to AWS | `make deploy/signin ENV=prod` |
| `make deploy` | Deploy ALL functions | `make deploy ENV=prod` |
| `make dist/<func>.zip` | Build deployment ZIP | `make dist/signin.zip` |
| `make dist` | Build ALL ZIPs | `make dist` |
| `make .env` | Download secrets from S3 | `make .env ENV=prod` |
| `make setmem/<func>` | Set function memory | `make setmem/signin SIZE=512` |
| `make connect` | Test API endpoint | `make connect METHOD=POST ENDPOINT=/signin PAYLOAD=tests/data/signin.json` |
| `make api` | Deploy API Gateway | `make api VERS=0.6 UPDATE=<id> STAGE=dev` |
| `make clean` | Remove build artifacts | `make clean` |

## API / Interface

**Lambda function structure:**
```python
# src/<function>/index.py
from lib import common
# from lib import env  # if you need secrets

def handler(event, context):
    # event: API Gateway event or custom event JSON
    # context: Lambda context object (simulated locally by MockContext)
    #   context.identity.cognito_identity_id — Cognito user identity
    #   context.aws_request_id — unique request ID
    #   context.function_name — function name
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "success"})
    }
```

**Error handling pattern (from example_func):**
```python
try:
    # ... your logic ...
except common.SAError as e:
    print(e)
    raise Exception('error: custom_failed')
except KeyError as e:
    print(common.SAError("accessing unknown property"))
    raise Exception('error: property_failed')
except Exception as e:
    print(common.SAError("unknown error of type %s" % type(e)))
    raise Exception('error: generic_failed')
```

**Environment variables** (from `lib/env.py`, sourced from S3):
- `API_HOST` — API Gateway host
- `API_ENDPOINT` — Full API Gateway URL
- `API_STAGE` — Stage name (e.g., `/dev`, `/prod`)
- `IDENTITY_POOL` — Cognito Identity Pool ID
- `AWS_ACCOUNT_ID` — AWS account number
- `CONFIG_MODE` — Environment (DEV, QA, PROD)

## Key Patterns

- **One function per directory**: Each Lambda function has its own `src/<name>/` directory
- **Shared lib directory**: Common code in `lib/` is copied into every function's ZIP
- **Environment from S3**: Config and secrets stored in S3, downloaded at build time, included in ZIP as `lib/env.py`
- **Swagger-first API design**: API Gateway defined in Swagger YAML, auto-deployed via `aws-apigateway-importer`
- **Local simulation**: `run.py` mocks Lambda's `event` and `context` objects for local testing
- **Cognito integration**: `connect.py` fetches temporary credentials and signs API requests
- **Identity caching**: `.identity_<CONFIG_MODE>` files cache Cognito identities between runs

## Environment

**Required local setup:**
- Python 3.x (3.9+ recommended; the code already uses Python 3 imports)
- AWS CLI configured with credentials
- S3 bucket for Lambda function storage
- S3 bucket containing `${ENV}_creds` file

**Required AWS resources:**
- Lambda execution role (IAM role with permissions for your functions)
- API Gateway (created/updated via Swagger)
- Cognito Identity Pool (if using authenticated APIs)

**Makefile configuration** (currently hardcoded — should be parameterized):
- `sportarchive-${ENV}-code` — S3 bucket for Lambda ZIPs and creds
- `lambda_orchestrate_role` — Lambda execution role name
- `ENV` — Environment: dev (default), prod
- `PROFILE` — AWS CLI profile (optional)

<!-- Ask: What are the actual S3 bucket names and IAM role ARNs for dev/qa/prod? -->
<!-- Ask: Should we parameterize these values (move to env vars or config file)? -->

## Deployment

**First-time setup:**
1. Create `${ENV}_creds` file with required variables (see Environment variables above)
2. Upload to S3: `aws s3 cp ${ENV}_creds s3://sportarchive-${ENV}-code/${ENV}_creds`
3. Update Makefile with correct S3 buckets and IAM role ARNs if different
4. Run `make .env` to download and generate `lib/env.py`
5. Create Lambda functions: `make create/<function> DESC='description'`

**Updates:**
1. Make code changes
2. Test locally: `make run/<function> EVENT=tests/data/test.json`
3. Run tests: `make test`
4. Deploy: `make deploy/<function>` (or `make deploy/<function> ENV=prod`)

**What `make deploy/<func>` does:**
1. Builds `dist/<func>.zip` (function code + lib/ + build/ dependencies)
2. Uploads ZIP to S3 (`s3://sportarchive-${ENV}-code/lambda/<func>.zip`)
3. Updates Lambda function code (`aws lambda update-function-code`)
4. Runs `scripts/lambda_configuration_update.sh` (sets runtime to python3.8)

<!-- Ask: Is there a CI/CD pipeline, or is deployment manual only? -->
<!-- Ask: How are Swagger files deployed — manual Makefile command or automated? -->

## Testing

**Unit tests:**
- Files: `tests/test*.py` (auto-discovered by `python -m unittest discover`)
- Each test file can contain multiple test classes inheriting `unittest.TestCase`
- Import handlers: `from src.<function>.index import handler`
- Run: `make test` (all) or `make test/<test-name>` (specific, name is part after "test")

**IMPORTANT:** Tests require `lib/env.py` to exist (run `make .env` first). MockContext makes live Cognito API calls, so AWS credentials must be configured.

**Local integration testing:**
- `make run/<function> EVENT=events/<test-event>.json`
- Create test event JSON files in `tests/data/`
- The `%IDENTITY_ID%` placeholder in event JSON is replaced with actual Cognito identity

**API Gateway testing:**
- `make connect ENDPOINT=/path METHOD=GET QUERY="key=val"`
- Full flow: Cognito unauthenticated identity -> temporary credentials -> SigV4 signed request -> API Gateway -> Lambda
- Requires Cognito Identity Pool configured and accessible

## Known Issues

See `FINDINGS.md` for the full audit. Key issues:

1. **Secrets bundled in ZIPs** (Critical) — `lib/env.py` with secrets is included in every Lambda deployment package
2. **Python 3.8 runtime EOL** (High) — Hardcoded in Makefile and scripts; must upgrade to 3.12
3. **Tests are broken** (Medium) — `testExampleFunc.py` references `src.assets` instead of `src.example_func`
4. **Tests require live AWS** (Medium) — MockContext makes real Cognito API calls
5. **Open security PR** (High) — Dependabot PR #6 for requests CVE-2024-35195 has been open 15+ months
6. **boto3 version very outdated** (Medium) — Pinned to 1.12.8 (Feb 2020), current is 1.35+

## Gotchas

- **`make .env` is a prerequisite for EVERYTHING** — Without it, `lib/env.py` doesn't exist and all Python imports fail. This is the #1 source of confusion for new developers.
- **Python 3.8 is EOL**: Lambda runtime in Makefile is hardcoded to python3.8. New function creation will fail. Upgrade to python3.12.
- **Hardcoded S3 buckets**: Makefile has hardcoded `sportarchive-${ENV}-code` bucket name. Make this configurable for other environments.
- **Submodule dependency**: `aws-apigateway-importer` is a Git submodule (deprecated). Run `git submodule update --init` after cloning, or use `aws apigateway import-rest-api` instead.
- **lib/ copied into every function**: Shared code in `lib/` is duplicated in every function's ZIP. For large shared libraries, consider Lambda Layers.
- **Secrets in ZIP**: The `env.py` file with secrets is bundled into function ZIPs. Use AWS Secrets Manager or Parameter Store for new functions.
- **Manual API Gateway deployment**: Swagger files must be manually deployed. Consider AWS SAM or CDK.
- **No Lambda Layers support**: Framework predates Lambda Layers.
- **Cognito unauthenticated tokens**: `connect.py` uses unauthenticated Cognito identities.
- **`sed -i` in Makefile**: The `api` target uses GNU `sed -i` which fails on macOS. Use `sed -i ''` for compatibility.
- **Region hardcoded**: `us-east-1` is hardcoded in `lib/apiconnect.py:75`. Cannot test other regions without code change.
- **`run.py` has no timeout**: `MockContext.get_remaining_time_in_millis()` returns infinity. Functions won't timeout locally like they do in Lambda.
- **GitHub backup workflow broken**: `.github/workflows/github-backup.yml` triggers on `develop` branch, but repo uses `master`.

<!-- Ask: Has this framework been replaced by AWS SAM or Serverless Framework in newer projects? -->
<!-- Ask: Are there any active Lambda functions still using this framework? -->
<!-- Ask: Should we migrate to SAM/CDK for new development? -->
