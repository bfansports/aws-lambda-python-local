# aws-lambda-python-local

## What This Is

A Python development framework for writing, testing, and deploying AWS Lambda functions. Provides local execution environment that simulates Lambda's `event` and `context` objects, Cognito integration for testing authenticated APIs, API Gateway management via Swagger, and Makefile-driven deployment workflow.

**Use case**: Rapid Lambda function development with local testing before deploying to AWS.

## Tech Stack

- **Language**: Python 2.7 (legacy; may need upgrade to Python 3.9+)
- **AWS Services**: Lambda, API Gateway, Cognito, S3
- **Tools**:
  - `aws-cli` 1.9+ — AWS resource management
  - `aws-apigateway-importer` — Swagger-based API deployment (Git submodule)
  - `pip` 6+ — Python package management
- **Testing**: `unittest` module
- **Build**: `Makefile` — all operations (build, test, deploy, run)

## Quick Start

```bash
# Setup
pip install -r requirements.txt
aws configure  # Set up AWS credentials

# Create a new Lambda function
# 1. Create src/<function-name>/ directory
# 2. Add src/<function-name>/index.py with handler function
# 3. Add src/<function-name>/__init__.py

# Run locally
make run/<function> EVENT=events/test.json

# Create function in AWS Lambda (first time)
make create/<function>

# Deploy (update existing function)
make deploy/<function>

# Run unit tests
make test
make test/<specific-test>

# Connect to secure API via Cognito
make connect ENDPOINT=/my_endpoint METHOD=GET QUERY="param=value"
```

## Project Structure

- `src/` — Lambda function source code (one subdirectory per function)
  - `src/<function>/index.py` — Entry point with `handler(event, context)` function
  - `src/<function>/__init__.py` — Required for Python module
- `lib/` — Shared libraries imported by multiple functions
- `tests/` — Unit tests (files named `test*.py`)
- `swagger/` — Swagger YAML files for API Gateway definition
- `scripts/` — Utility scripts
- `requirements.txt` — Python dependencies (installed into each function's ZIP)
- `Makefile` — Build, test, deploy automation
- `run.py` — Local Lambda simulator script
- `connect.py` — API Gateway + Cognito test client

## Dependencies

**External:**
- AWS Lambda — function execution environment
- AWS API Gateway — HTTP API layer
- AWS Cognito — authentication and temporary credentials
- AWS S3 — function code storage (ZIP files uploaded to S3 before Lambda update)

**Internal:**
- `lib/` directory — shared code copied into each function's ZIP
- `.env` file — environment variables and secrets (downloaded from S3)

<!-- Ask: What S3 bucket is used for Lambda function storage? -->
<!-- Ask: Is this framework still in use, or has it been replaced by SAM/Serverless Framework? -->

## API / Interface

**Lambda function structure:**
```python
# src/<function>/index.py
def handler(event, context):
    # event: API Gateway event or custom event JSON
    # context: Lambda context object (simulated locally)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "success"})
    }
```

**Makefile commands:**
- `make create/<function>` — Create new Lambda function in AWS
- `make deploy/<function> [ENV=prod]` — Update existing Lambda function
- `make run/<function> [EVENT=file] [VERBOSE=1]` — Run locally
- `make dist/<function>.zip` — Build deployment ZIP
- `make test` — Run all unit tests
- `make connect ENDPOINT=/path METHOD=GET` — Test API Gateway with Cognito auth

**Environment variables** (from `.env` file in S3):
- `API_HOST` — API Gateway host
- `API_ENDPOINT` — Full API Gateway URL
- `API_STAGE` — Stage name (e.g., `/dev`, `/prod`)
- `IDENTITY_POOL` — Cognito Identity Pool ID
- `AWS_ACCOUNT_ID` — AWS account number
- `CONFIG_MODE` — Environment (DEV, QA, PROD)

## Key Patterns

- **One function per directory**: Each Lambda function has its own `src/<name>/` directory
- **Shared lib directory**: Common code in `lib/` is copied into every function's ZIP
- **Environment from S3**: Config and secrets are stored in S3, downloaded at build time, and included in ZIP as `lib/env.py`
- **Swagger-first API design**: API Gateway is defined in Swagger YAML, auto-deployed via `aws-apigateway-importer`
- **Local simulation**: `run.py` mocks Lambda's `event` and `context` objects for local testing
- **Cognito integration**: `connect.py` fetches temporary credentials and signs API requests

## Environment

**Required local setup:**
- Python 2.7 (or 3.x if migrated)
- AWS CLI configured with credentials
- S3 bucket for Lambda function storage
- S3 bucket for `.env` file storage

**Required AWS resources:**
- Lambda execution role (IAM role with permissions for your functions)
- API Gateway (created/updated via Swagger)
- Cognito Identity Pool (if using authenticated APIs)

**Environment variables** (local development):
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` — Set via `aws configure`

**Makefile configuration** (hardcoded in Makefile — should be parameterized):
- `AWS_BUCKET_CODE` — S3 bucket for Lambda ZIPs
- `IAM_ROLE` — Lambda execution role ARN
- `ENV` — Environment (DEV, QA, PROD)
- `PROFILE` — AWS CLI profile (optional)

<!-- Ask: What are the actual S3 bucket names and IAM role ARNs for dev/qa/prod? -->
<!-- Ask: Should we parameterize these values (move to env vars or config file)? -->

## Deployment

**First-time setup:**
1. Create `.env` file with required variables
2. Upload `.env` to S3 at the path expected by Makefile
3. Update Makefile with correct S3 buckets and IAM role ARNs
4. Create Lambda functions: `make create/<function>`

**Updates:**
1. Make code changes
2. Test locally: `make run/<function>`
3. Deploy: `make deploy/<function>`

**API Gateway deployment:**
1. Update Swagger YAML in `swagger/` directory
2. Run `aws-apigateway-importer` (see Makefile)
3. Deploy to stage

<!-- Ask: Is there a CI/CD pipeline, or is deployment manual? -->
<!-- Ask: How are Swagger files deployed — manual Makefile command or automated? -->

## Testing

**Unit tests:**
- Write test cases in `tests/test*.py`
- Each test file can contain multiple test classes
- Import Lambda handlers: `from src.<function>.index import handler`
- Run: `make test` (all) or `make test/<test-name>` (specific)

**Local integration testing:**
- Use `make run/<function> EVENT=events/<test-event>.json`
- Create test event JSON files for different scenarios
- Verify output matches expected results

**API Gateway testing:**
- Use `make connect ENDPOINT=/path METHOD=GET QUERY="key=val"`
- Tests full flow: Cognito auth → API Gateway → Lambda
- Requires Cognito Identity Pool configured

## Gotchas

- **Python 2.7 is EOL**: This framework uses Python 2.7, which is no longer supported. Lambda supports Python 3.9+. Migration recommended.
- **Hardcoded S3 buckets**: Makefile has hardcoded S3 bucket names and IAM role ARNs. Make these configurable.
- **Submodule dependency**: `aws-apigateway-importer` is a Git submodule. Run `git submodule update --init` after cloning.
- **lib/ copied into every function**: Shared code in `lib/` is duplicated in every function's ZIP. For large shared libraries, consider Lambda Layers instead.
- **Environment secrets in ZIP**: The `.env` file is bundled into the function ZIP. For sensitive secrets, use AWS Secrets Manager or Parameter Store instead.
- **Manual API Gateway deployment**: Swagger files must be manually deployed via `aws-apigateway-importer`. Consider AWS SAM or Terraform for automated API management.
- **No Lambda Layers support**: This framework predates Lambda Layers. For shared dependencies, use Layers instead of copying `lib/` into every ZIP.
- **Cognito unauthenticated tokens**: `connect.py` uses unauthenticated Cognito identities. For authenticated testing, add user pool integration.

<!-- Ask: Has this framework been replaced by AWS SAM or Serverless Framework in newer projects? -->
<!-- Ask: Are there any active Lambda functions still using this framework? -->
<!-- Ask: Should we migrate to SAM/CDK for new development? -->