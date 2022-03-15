import logging
import json
import os, re
import logging
import datetime, time
from requests import get, post
from json import JSONEncoder


import azure.functions as func



def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Invoked AnalyzeInvoice Skill.')
    try:
        body = json.dumps(req.get_json())
        if body:
            logging.info(body)
            result = compose_response(body)
            return func.HttpResponse(result, mimetype="application/json")
        else:
            return func.HttpResponse(
                "Invalid body",
                status_code=400
            )
    except ValueError:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )
def compose_response(json_data):
    values = json.loads(json_data)['values']
    
    # Prepare the Output before the loop
    results = {}
    results["values"] = []
    
    
    for value in values:
        output_record = transform_value(value)
        if output_record != None:
            results["values"].append(output_record)
    return json.dumps(results)

## Perform an operation on a record
def transform_value(value):
    result = {}
    try:
        recordId = value['recordId']
    except AssertionError  as error:
        return None
    # Validate the inputs
    first = True
    prev = ""
    try:
        result = {}
        assert ('data' in value), "'data' field is required."
        data = value['data']['kvp']   
        for key, val in data.items(): 
            if re.search('opening', key, re.IGNORECASE):
                result["opening_balance"] = value
            elif re.search('deposits', key, re.IGNORECASE):
                result["deposits_and_credits"] = value
            elif re.search('debits', key, re.IGNORECASE):
                result["debits_and_withdrawals"] = value
            elif re.search('ending', key, re.IGNORECASE):
                result["ending_balance"] = value
            elif re.search('closing', key, re.IGNORECASE):
                result["ending_balance"] = val
            elif re.search('beginning', key, re.IGNORECASE):
                result["opening_balance"] = val
            elif re.search('credits', key, re.IGNORECASE):
                result["deposits_and_credits"] = val
            else:
                result[key.replace(" ", "_")] = value

            
    except AssertionError  as error:
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Error:" + error.args[0] }   ]       
            })
    except Exception as error:
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Error:" + str(error) }   ]       
            })
    return ({
            "recordId": recordId,   
            "data": {
                "sow": sow,
                "cr": cr
            }
            })
