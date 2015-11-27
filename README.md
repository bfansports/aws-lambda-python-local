# AWS Lambda Python Local environment

This tool provides a framework for writing, packaging, testing and
deploying Python AWS Lambda functions.

It's all done with a Makefile.

## Setup your env

* Python 2.7
* Pip 6+
* aws-cli 1.9+

Install AWS CLI tool:
http://docs.aws.amazon.com/cli/latest/userguide/installing.html#install-with-pip

Configure credentials:
http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html

## AWS Cognito support

If you don't know AWS Cognito, see: https://aws.amazon.com/cognito/

It allows you to give a unique identity to your users no matter on which device they're on. Pretty handy for providing credentials to your AWS resources like API Gateway for example.

When using Cognito + API Gateway + Lambda, you can achieve a Serverless backend for your API. The Cognito IdentityId is passed along all the way down to your lambda function. You can then identify your user in Lambda for your logic.

## Lambda Context Support

This framework supports a MockContext that simulate the `context` variable you would receive in the real Lambda environment.

     # src/<function>/index.py
     def handler(event, context):
        ...

In `context` you will find your AWS Cognito Identity Pool ID and IdentityId that the script will get for you.

Check the `tests/MockContext.py` file and change the `self.identity.cognito_identity_pool_id` to point to your Identity Pool.

If you don't want Cognito, then just comment this out and put whatever in `self.identity.cognito_identity_id`.

## Writing Functions

Function code goes in the `src/` directory. Each function must be in a
sub-directory named after the function. For example, if the Lambda
function name is "signin", the code goes in the `src/signin`
directory.

*Note:* Make sure you put an `__init__.py` in your folder and any
 subfolders.

### Entry Point

The entrypoint for each function should be in an `index.py` file,
inside of which should be a function named `handler`. See the AWS
Lambda documentation for more details on how to write the handler.

       # src/<function>/index.py
       def handler(event, context):
       	   ...

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

## Testing

### Running Functions Locally

Before building and deploying, you sure want to test your code
first. In order to simulate the Lambda environment, a script is
provided that will execute your function as if it was in AWS Lambda.

	usage: make run/FUNCTION [VERBOSE=1] [EVENT=filename]

	Run a Lambda function locally.

	optional arguments:
	  VERBOSE=1       Sets verbose output for the function
	  EVENT=filename  Load an event from a file rather than stdin. JSON file with the content to provide.

If you don't specify EVENT, `make run/%` will take a JSON event from a standard input (stdin).
Stdin is good to use for functions that don't take any input. Just send an empty object by typing `{}` and then exit from stdin by typing `ctrl-d`.

### Writing Unit Tests

For automated testing, you can write unit tests using Python's
`unittest` module.

* All test cases must be in a file called `test*.py` in the `tests`
  directory. Any example is `testModule.py`.
* Each file can contain any number of test cases, but each must
  inherit from `unittest.TestCase`.
* In tests, you can import the handler for a Lambda function with:
  `import src.<MODULE_NAME>.index`, and then using `.handler`.

All the unit tests can be run using `make test`. It auto-discovers all
test cases that follow the above rules. To run a specific test, just
run `make test/<TEST>`, replacing `<TEST>` with the name of the test
(i.e., the part of the test's filename after "test"; as an example,
the file "testUpload.py" has the name "upload").

## Building

Once your function is written, it can be built into a ZIP file.

	make dist/<function>.zip

Run the above command to build a ZIP archive for "function". It will
automatically get the necessary Python packages.

Note: If you didn't get the Python modules. Just run first:

        make clean

You can also run `make all` or `make dist` to build all of the
functions.

## Creating

If the function is new you must create it in AWS.

        make create/<function>

This will create the function in lambda. It will `build` it first and then zip it and send it over to AWS Lambda.
You can then update it using `make deploy/<function>" below.

## Deploying

You made a quick update, now you must deploy the Lambda function. *First the Lambda function
needs to be created in AWS*

        make deploy/<function>

This will build the ZIP file, upload it to S3, and finally update the
function code on Lambda.

You also simply run `make deploy` to deploy ALL your functions in `src`.
