import logging
import json
import os
import logging
import datetime, time
from requests import get, post
from json import JSONEncoder
from azure.ai.formrecognizer import FormRecognizerClient
from azure.ai.formrecognizer import FormTrainingClient
from azure.core.credentials import AzureKeyCredential

import azure.functions as func

class DateTimeEncoder(JSONEncoder):
        #Override the default method
        def default(self, obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Invoked AnalyzeGeneralDocument Skill.')
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
    endpoint = os.environ["FORMS_RECOGNIZER_ENDPOINT"]
    key = os.environ["FORMS_RECOGNIZER_KEY"]
    form_recognizer_client = FormRecognizerClient(endpoint, AzureKeyCredential(key))
    for value in values:
        output_record = transform_value(value, endpoint, key)
        if output_record != None:
            results["values"].append(output_record)
    return json.dumps(results, ensure_ascii=False, cls=DateTimeEncoder)

## Perform an operation on a record
def transform_value(value, endpoint, key):
    try:
        recordId = value['recordId']
    except AssertionError  as error:
        return None
    # Validate the inputs
    try:         
        assert ('data' in value), "'data' field is required."
        data = value['data']   
        logging.info(data)
        form_url = data["formUrl"]  + data["formSasToken"]   
        logging.info(form_url)
        url = f"{endpoint}formrecognizer/documentModels/prebuilt-document:analyze?api-version=2021-09-30-preview"
        headers = {
            # Request headers
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': key,
        }
        body = { 
        "urlSource": form_url
        }
        params = {  "locale": "en-US" }
        resp = post(url = url, data = json.dumps(body), headers = headers, params = params)
        if resp.status_code != 202:
            logging.info("POST analyze failed:\n%s" % resp.text)
        else:
            logging.info("POST analyze succeeded:\n")
            get_url = resp.headers["operation-location"]
            logging.info(get_url)
            result = {}
            entities = []
            tables = []
            tries = 5
            for attempt in range(tries):
                resp = get(url = get_url, headers = {"Ocp-Apim-Subscription-Key": key})
                resp_json = json.loads(resp.text)
                if resp.status_code != 200:
                    logging.info("GET Document results failed:\n%s" % resp_json)
                    break
                status = resp_json["status"]
                if status == "succeeded":
                    logging.info("GET Document results succeded:\n" )
                    for item in resp_json["analyzeResult"]["keyValuePairs"]:
                        if "key" in item and "value" in item:
                            logging.info(f"{item['key']['content']} \t\t Value: {item['value']['content']}")
                            result[item['key']['content']] = item['value']['content']
                        else:
                            logging.info("Both key and value need to exist")
                    tables = resp_json["analyzeResult"]["tables"]
                    for table in tables:
                        for cell in table["cells"]:
                            cell.pop("boundingRegions", None)
                            cell.pop("spans", None)
                        table.pop("boundingRegions", None)
                        table.pop("spans", None)
                    entities = resp_json["analyzeResult"]["entities"]
                    for entity in entities:
                        entity.pop("boundingRegions", None)
                        entity.pop("spans", None)
                    
                    break
                if status == "failed":
                    prilogging.infont("Analysis failed:\n%s" % resp_json)
                    break
                time.sleep(3)


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
                "key_value_pairs": result,
                "entities": entities,
                "tables": tables
            }
            })
