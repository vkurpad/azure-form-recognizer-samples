import json, time
from requests import get, post
import time
import concurrent.futures
from concurrent.futures import as_completed, wait
from os import listdir, walk, path
from os.path import isfile, join
import csv   

#####################################################
# This scripts reads all PDF files in a folder and submits them for processing to the Form Recognizer prebuilt document endpoint. The results are stored back in the current folder.
# The goal of this script is to bulk process the files maintaining the highest throughput 
####################################################

# The average load we want to maintain on the service
batch_size = 100

# number of threads we can run in parallel
num_threads = 10
def init():
    fields=['Stage','File','Operation Location', 'Status Code', 'Error']
    with open(r'errors.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(fields)

docs_processed = {}
def save_result(resp_json, file_name):
    with open(f"{path.basename(file_name)}.res.json", 'w') as outfile:
        outfile.write(json.dumps(resp_json))
def log_error(stage, doc, op_loc, status, err):
    fields=[stage, doc, op_loc, status, err]
    with open(r'errors.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(fields)

def send_request(type, url, input_file, retry_count=0):    
    # TODO Update The endpoint and Key
    endpoint = "Your Form Recognizer Endpoint "
    apim_key = "Your Form Recognizer Key "
    api_version = "2022-08-31"
    model_id = "prebuilt-document"
    if type == "post":
        print(f"Sending File ------------------{input_file}")
        post_url = endpoint + f"/formrecognizer/documentModels/{model_id}:analyze?api-version={api_version}"
        headers = {
            # Request headers
            'Content-Type': 'application/octet-stream',
            'Ocp-Apim-Subscription-Key': apim_key,
        }
        with open(input_file, "rb") as fd:
        
            document = fd.read()
            try:
                resp = post(url = post_url, data = document, headers = headers, params = None)
                if resp.status_code == 202:
                    get_url = resp.headers["operation-location"]
                    return {
                    "status_code": resp.status_code,
                    "operation_location": get_url,
                    "status" :"success",
                    "document" : input_file
                }
                else:
                    return {
                    "status_code": resp.status_code,
                    "operation_location": None,
                    "status" :"failed",
                    "document" : input_file
                }
            except Exception as e:
                return {
                    "status_code": str(e),
                    "operation_location": None,
                    "status" :"failed",
                    "document" : input_file
                }
    else:
        print("Checking for status on active requests ------------------")
        try:
            resp = get(url = url, headers = {"Ocp-Apim-Subscription-Key": apim_key})
            resp_json = json.loads(resp.text)
            
            if resp.status_code != 200:
                return {
                    "status_code": resp.status_code,
                    "operation_location": url,
                    "status" :"failed"
                }
            status = resp_json["status"]
            return resp_json
            
        except Exception as e:
            return {
                    "status_code": str(e),
                    "operation_location": url,
                    "status" :"failed"
                }

def submit(input_file):
    retry = 0
    while retry < 3:

        # If the request was successful return the result
        result = send_request("post", None, input_file)
        if result["status_code"] == 202:
            return result
        if result["status_code"] == 429:
            retry = retry + 1
        else:
            break
    # Not successful and retries also failed. log and continue
    log_error("Submit", result["document"], None, result["status_code"], result["status"])
    return result


        


def check_for_completion(results):
    for res in results:
        if(res["status"] == "success"):
            resp_json = send_request("get", res["operation_location"], None)
            if  resp_json["status"] ==  "succeeded":

                ##############  TODO: Save the file here ######################### 
                save_result(resp_json, res["document"])
                res["status"] = "completed"
        else:
            log_error("Get Results", res["document"], None, resp_json["status_code"], resp_json["status"])

    results = [i for i in results if i and not i['status'] == "completed"]
    return results

def main():
    # Read all files from the folder. Currently assume you do not want to process subfolders. 
    #TODO Update as needed
    folder = "../testdata"
    init()
    files = []
    for (dirpath, dirnames, filenames) in walk(folder):
        # Filtering to only PDF files
        #TODO Update filter as needed
        filenames = [ fi for fi in filenames if  fi.endswith(".pdf") ]
        files.extend(filenames)
        break
    initial = files[:batch_size]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers = num_threads) as executor:
        # Submit files for processing
        futures = [executor.submit(submit, f"{folder}/{doc}") for doc in initial]
        for future in as_completed(futures):
            results.append(future.result())
            # result is the dict containing info on the post request
        wait(futures)
        processed = len(initial)
        completed = 0
        # While there are still more files to process....
        while processed < len(files):
            # Trying to keep a steady load of 100 documents being processed. As documents complete, submit the same number
            results = [i for i in results if i ]
            results = check_for_completion(results)
            completed = batch_size - len(results)
            if completed == 0:
                # Back off for 3 seconds if none of the documents has completed
                time.sleep(3)
                continue
            # Take the next set of files to fill the batch
            current  = files[processed : processed + completed]
            futures = [executor.submit(submit, f"{folder}/{doc}") for doc in current]
            processed += completed
            for future in as_completed(futures):
                results.append(future.result())

        while len(results) > 0:
            results = check_for_completion(results)
        
        print("All documents processed successfully")
        
main()


