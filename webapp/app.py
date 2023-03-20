import re, json, os
from datetime import datetime
from flask import render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import string, random, requests
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos import exceptions, CosmosClient, PartitionKey


from flask import Flask

app = Flask(__name__)
storage_account =  os.environ.get('STORAGE_ACCOUNT', 'storageAccount')
storage_account_key = os.environ.get('STORAGE_ACCOUNT_KEY', 'storageAccountKey')
cosmos_url = os.environ.get('COSMOS_URL', 'cosmosUrl')
cosmos_key = os.environ.get('COSMOS_KEY', 'cosmosKey')
fr_endpoint =  os.environ.get('FR_ENDPOINT', 'frEndpoint')
fr_key = os.environ.get('FR_KEY', 'frKey')
cosmos_db = "mechanics_docs"
cosmos_container = "analyzed_docs"
storage_container = "fr-mechanics"


blob_service_client = BlobServiceClient(account_url=f"https://{storage_account}.blob.core.windows.net/", credential=storage_account_key)
client = CosmosClient(cosmos_url, cosmos_key)


# Replace the existing home function with the one below
@app.route("/")
def home():
    return render_template("home.html", storage_account=storage_account)

# New functions
@app.route("/about/")
def about():
    return render_template("about.html")

@app.route("/contact/")
def contact():
    return render_template("contact.html")

@app.route("/setup/")
def setup():
    
    try:
        database = client.create_database(id=cosmos_db)
    except exceptions.CosmosResourceExistsError:
        database = client.get_database_client(database=cosmos_db)
    
    try:
        container = database.create_container(id=cosmos_container, partition_key=PartitionKey(path="/id", kind="Hash"))
    except exceptions.CosmosResourceExistsError:
        container = database.get_container_client(cosmos_container)
    return render_template("setup.html")


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        try:
            blob_client = blob_service_client.get_blob_client(container=storage_container, blob=filename)
            blob_client.upload_blob(file)
        except Exception as ex:
            print('Exception=' + str(ex) )
            pass
        ref =  f'http://{storage_account}.blob.core.windows.net/{storage_container}/' + filename
        file.seek(0, 0)
        document_analysis_client = DocumentAnalysisClient(endpoint=fr_endpoint, credential=AzureKeyCredential(fr_key))
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-document", document=file
        )
        result = poller.result()
        for kv_pair in result.key_value_pairs:
            if kv_pair.key:
                print( f"Key {kv_pair.key.content} found")
            if kv_pair.value:
                print( f"Value {kv_pair.value.content} found")
        
        database = client.get_database_client(cosmos_db)
        container = database.get_container_client(cosmos_container)
        d = [kvp.to_dict() for kvp in result.key_value_pairs]
        result = { "id": filename, "ref": ref, "key_value_pairs": d}
        container.create_item(body=result)
        #print("Successfully processed document: " + filename)
        return render_template("upload.html", method="POST", ref=ref, kv_pair = d) 
    else:
        print("In the GET operation")
        return render_template("upload.html", method="GET")