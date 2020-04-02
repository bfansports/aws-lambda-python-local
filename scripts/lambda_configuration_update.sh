#!/bin/bash

FUNC=$1

OUT=`aws lambda update-function-configuration \
      --function-name ${FUNC} \
      --runtime python3.8`
