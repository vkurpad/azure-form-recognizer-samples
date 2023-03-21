import re, json, os
from datetime import datetime
from flask import render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import string, random, requests
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.ai.formrecognizer import DocumentAnalysisClient, DocumentModelAdministrationClient
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
document_analysis_client = DocumentAnalysisClient(endpoint=fr_endpoint, credential=AzureKeyCredential(fr_key))
document_model_client = DocumentModelAdministrationClient(endpoint=fr_endpoint, credential=AzureKeyCredential(fr_key))
database = client.get_database_client(cosmos_db)
container = database.get_container_client(cosmos_container)
# Replace the existing home function with the one below
@app.route("/")
def home():
    items = []
    item_list = list(container.query_items( query="SELECT * FROM c ORDER BY c._ts DESC", enable_cross_partition_query=True, max_item_count=10)) 
    for doc in item_list:
        fields = doc.get("fields")
        temp = []
        for field in fields:
            if field.get("key") == "InvoiceId":
                temp.append({"pos": 0, "value": field})
            elif field.get("key") == "CustomerName":
                temp.append({"pos": 1, "value": field})
            elif field.get("key") == "CustomerAddress":
                temp.append({"pos": 2, "value": field})
            elif field.get("key") == "DueDate":
                temp.append({"pos": 3, "value": field})
            elif field.get("key") == "InvoiceTotal":
                temp.append({"pos": 4, "value": field})
            elif field.get("key") == "VendorName":
                temp.append({"pos": 5, "value": field})
        sorted_lst = sorted(temp, key=lambda k: k['pos'])
        items.append(sorted_lst)
    return render_template("home.html", rows=items)

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
        model_id = request.form["model_id"]
        try:
            blob_client = blob_service_client.get_blob_client(container=storage_container, blob=filename)
            blob_client.upload_blob(file)
        except Exception as ex:
            print('Exception=' + str(ex) )
            pass
        ref =  f'http://{storage_account}.blob.core.windows.net/{storage_container}/' + filename
        file.seek(0, 0)
        
        poller = document_analysis_client.begin_analyze_document(
            model_id, document=file
        )
        result = poller.result()
        
        
        d = [kvp.to_dict() for kvp in result.key_value_pairs]
        if len(result.documents) > 0:
            fields = []
            for key, value in result.documents[0].fields.items():
                if value.value_type != "list":
                    fields.append({"key": key, "value": value.content})
                else:
                   
                    count = 0
                    for v in value.value:
                        cols = []
                        for col, cell in v.value.items():
                            cols.append({"key": col, "value": cell.content})
                        fields.append({"key": "row-" + str(count), "value": cols}) 
                        count = count + 1
            f = fields
                    
        else:
            f = None
        result = { "id": filename, "ref": ref, "key_value_pairs": d, "fields": f}
        container.create_item(body=result)
        #print("Successfully processed document: " + filename)
        return render_template("upload.html", method="POST", ref=ref, kv_pair=d) 
    else:
        print("In the GET operation")
        models = document_model_client.list_document_models()

        return render_template("upload.html", method="GET", models=models)