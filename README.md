# Dev, Create, Deploy and Test API Gateway + Python Lambda Functions

This repository provides a framework for writing, packaging, and
deploying Python lambda functions to AWS.

You can also auto create, update and deploy your API on AWS API Gateway. You can also test connectivity to it.

If you use Cognito for temporary credentials, the framework will get you an Unauthenticated token and temporary credentials to connect to your Secure API endpoint.

You can simluate a Mobile App behavior and play the entire flow locally:<br>
`Cognito -> Connect to API -> Call Lambda function -> Parse result file`

## Cognito

If your API is not public and is secured by IAM Roles, you will need the proper credentials to connect to it. Cognito allows your clients to obtain an identity and a token they can obtain temporary Credentials.

Those credentials are set by AWS IAM roles and grant access to AWS services. In our case, the services we need access to are: AWS API Gateway and AWS Lambda (if your lambda function is configured to pass through user credentials)

## API Gateway & Swagger

You should define your API in a description file. Swagger is a tool that provides a YAML format for describing your API. It also generates documentation for you and an online service: http://swaggerhub.com

AWS supports swagger files in order to create your API. There is an example of a yaml file in the "swagger" folder that respects the Swagger/AWS format and requirements.

Using the `aws-apigateway-importer` program provided by AWS and added as a submodule here, you can automatically create, update and deploy your API in AWS. No need for console anymore.

The YAML file is authoriative and always accurratly describes your API. 

## Setup your env

* Python 2.7
* Pip 6+
* aws-cli 1.9+

Install AWS CLI tool:
http://docs.aws.amazon.com/cli/latest/userguide/installing.html#install-with-pip

Configure credentials:
http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html

If you have some issues with dependencies, consider using VirtualEnv for Python.

## Writing Functions

Function code goes in the `src/` directory. Each function must be in a
sub-directory named after the function. For example, if the Lambda
function name is "signin", the code goes in the `src/signin`
directory.

*Note:* Make sure you put an `__init__.py` in your folder and any
 subfolders. Check existing functions.

### Entry Point

The entrypoint for each function should be in an `index.py` file,
inside of which should be a function named `handler`. See the AWS
Lambda documentation for more details on how to write the handler.

    # src/<function>/index.py
	def handler(event, context):
		...

See the example fuction in the `src` folder.

### Third-party Libraries

For a third-party library, use the `requirements.txt` file as you
would any Python package.  See the Python pip documentation for more
details:
https://pip.readthedocs.org/en/stable/user_guide/#requirements-files

### Internal Libraries

If you need to write a common library that will be shared among
multiple Lambda functions, but is not independent enough to warrant
its own package, you can use the `lib` directory.

Consider the `lib` directory to be a part of the `PYTHON_PATH`. This
means any module or sub-modules in that directory will be available in
any function. (Behind the scenes, the contents of the `lib` directory
are copied verbatim alongside the Lambda function source files.)

## Makefile

All actions are done through the Makefile. Just type `make` to see the help.

### Creating

If the function is new, you must create it in AWS Lambda.

        make create/<function>

This will create the function in AWS and will upload your code.

You can then update it using `make deploy/<function>` below.

### Building

Your functions can be built into a ZIP file.

	make dist/<function>.zip

Run the above command to build a ZIP archive for "function". It will
automatically get the necessary Python packages.

Note: If you didn't get the Python modules. Just run first:

        make clean

You can also run `make all` or `make dist` to build all of the
functions.

### Running

Before deploying, you want to test your Lambda code locally first.

In order to simulate the Lambda environment, a script is
provided that will execute your function as if it was in AWS Lambda.

	usage: make run/FUNCTION [VERBOSE=1] [EVENT=filename]

	This runs a Lambda function locally.

	optional arguments:
	  VERBOSE=1       Sets verbose output for the function
	  EVENT=filename  Load an event from a file rather than stdin. This file contain the input you want to send to your function.

The `make run/%` script will take a JSON event from a standard input
(or a file if you specify), and execute the function you specify.

This function will inject the proper data in the `event` and `context` variables like Lambda would. Your Cognito Identity ID will be injected too.

### Deploying

Finally, you can deploy a function by running:

	make deploy/<function> [ENV=prod]

This will build the ZIP file, upload it to S3, and finally update the
function code on Lambda.

As with building, you can call `make deploy` to simultaneously deploy
all Lambda functions. (Use this carefully.)

You want to specify ENV=prod if you want to pull the .env file from prod S3 and not the default DEV.
If you do so, make sure you have the AWS credentials setup correctly locally.

*Note:* You want to edit the Makefile to replace the S3 bucket used for uploading. Right now, our bucket is hardcoded in there...

### Connecting

If your API is secure, you can't test it in the AWS console nor in the browser anymore. You need to authenticate.

If you use Cognito, you can connect to your API by using this framework:

 	make connect ENDPOINT=/my_endpoint METHOD=GET QUERY="parm1=val1"

This will call your API and display the resulting data. We expect JSON.

See `lib/apiconnect.py` for more details. And see below for the required environment variables you need to get started.

## Environment & Secrets

In order for your Lambda functions to get secrets and environment variables, we provide a mechanism in the Makefile that downloads a file from S3 and transforms it as a env.py file that is being put in the `./lib` folder. This file can then be `import` in your functions and will be added in the resulting ZIP file before being sent out to AWS.

This allows your functions to be built and package with the proper environment.

### Details

If you want to use environment variables, just put the line below at the
top of your index.py file.

	from lib import env

To refresh the local .env file, delete it, and

   	make .env [ENV=prod]

We could download from S3 at runtime, but it slows down the Lambda function, and you pay for that...

Secrets such as the following can be added to this file in S3:
  - Environment variables
  - Secret API keys
  - Anything else that is external and dynamic

*Note:* The .env file will be stored locally from the environment file downloaded from S3.

*Note:* Edit the `.env` rule in the Makefile to download your configuration file from the S3 location you want. Right now the bucket is hardcoded and point to ours!

### Environment expected

Those are the required environment variables you MUST provide in your .env file. This is what you must put in the file located in S3. This will be converted to the `lib/env.py` file that can be injected in your Lambda functions.

    	API_HOST='xxxxxxxxxxxxxx.execute-api.us-east-1.amazonaws.com'
	API_ENDPOINT='https://xxxxxxxxxxxxxxx.execute-api.us-east-1.amazonaws.com'
	API_STAGE='/dev_06'
	IDENTITY_POOL='us-east-1:49d897f9-e8a3-459b-abf2-xxxxxxxxxxxxxxx'
	AWS_ACCOUNT_ID='xxxxxxxxxxxxxxx'
	CONFIG_MODE='DEV'

## Unit Tests

For automated testing, you can write unit tests using Python's
`unittest` module.

   * All test cases must be in a file called `test*.py` in the `tests` directory. Any example is `testModule.py`.
   * Each file can contain any number of test cases, but each must inherit from `unittest.TestCase`.
   * In tests, you can import the handler for a Lambda function with: `import src.<MODULE_NAME>.index`, and then using `.handler`.

All the unit tests can be run using `make test`. It auto-discovers all
test cases that follow the above rules. To run a specific test, just
run `make test/<TEST>`, replacing `<TEST>` with the name of the test
(i.e., the part of the test's filename after "test"; as an example,
the file "testUpload.py" has the name "upload").

## Credit

To @Parent5446 (https://github.com/Parent5446) who wrote most of this great framework.
