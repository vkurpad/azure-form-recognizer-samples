using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Threading;
using Azure;
using Azure.AI.FormRecognizer.DocumentAnalysis;
using System.IO;
namespace SDKSample_v3._0API
{
    class Program
    {
        public static string endpoint = "https://{endpoint}.cognitiveservices.azure.com/";
        public static string apiKey = "{FormRecKey}";


        static async Task Main(string[] args)
        {
            AzureKeyCredential credential = new AzureKeyCredential(apiKey);
            DocumentAnalysisClient client = new DocumentAnalysisClient(new Uri(endpoint), credential);
            DocumentModelAdministrationClient admin = new DocumentModelAdministrationClient(new Uri(endpoint), credential);



            // sample invoice document
            //await AnalyzeInvoice(client);
            //await BuildNeuralModel(admin);
            await AnalyzeCustomModel(client);

        }
        public static async Task AnalyzeInvoice(DocumentAnalysisClient client)
        {
            Uri invoiceUri = new Uri("https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-invoice.pdf");

            AnalyzeDocumentOperation operation = await client.StartAnalyzeDocumentFromUriAsync("prebuilt-invoice", invoiceUri);

            await operation.WaitForCompletionAsync();

            AnalyzeResult result = operation.Value;

            for (int i = 0; i < result.Documents.Count; i++)
            {
                Console.WriteLine($"Document {i}:");

                AnalyzedDocument document = result.Documents[i];

                if (document.Fields.TryGetValue("VendorName", out DocumentField? vendorNameField))
                {
                    if (vendorNameField.ValueType == DocumentFieldType.String)
                    {
                        string vendorName = vendorNameField.AsString();
                        Console.WriteLine($"Vendor Name: '{vendorName}', with confidence {vendorNameField.Confidence}");
                    }
                }

                if (document.Fields.TryGetValue("CustomerName", out DocumentField? customerNameField))
                {
                    if (customerNameField.ValueType == DocumentFieldType.String)
                    {
                        string customerName = customerNameField.AsString();
                        Console.WriteLine($"Customer Name: '{customerName}', with confidence {customerNameField.Confidence}");
                    }
                }

                if (document.Fields.TryGetValue("Items", out DocumentField? itemsField))
                {
                    if (itemsField.ValueType == DocumentFieldType.List)
                    {
                        foreach (DocumentField itemField in itemsField.AsList())
                        {
                            Console.WriteLine("Item:");

                            if (itemField.ValueType == DocumentFieldType.Dictionary)
                            {
                                IReadOnlyDictionary<string, DocumentField> itemFields = itemField.AsDictionary();

                                if (itemFields.TryGetValue("Description", out DocumentField? itemDescriptionField))
                                {
                                    if (itemDescriptionField.ValueType == DocumentFieldType.String)
                                    {
                                        string itemDescription = itemDescriptionField.AsString();

                                        Console.WriteLine($"  Description: '{itemDescription}', with confidence {itemDescriptionField.Confidence}");
                                    }
                                }

                                if (itemFields.TryGetValue("Amount", out DocumentField? itemAmountField))
                                {
                                    if (itemAmountField.ValueType == DocumentFieldType.Double)
                                    {
                                        double itemAmount = itemAmountField.AsDouble();

                                        Console.WriteLine($"  Amount: '{itemAmount}', with confidence {itemAmountField.Confidence}");
                                    }
                                }
                            }
                        }
                    }
                }

                if (document.Fields.TryGetValue("SubTotal", out DocumentField? subTotalField))
                {
                    if (subTotalField.ValueType == DocumentFieldType.Double)
                    {
                        double subTotal = subTotalField.AsDouble();
                        Console.WriteLine($"Sub Total: '{subTotal}', with confidence {subTotalField.Confidence}");
                    }
                }

                if (document.Fields.TryGetValue("TotalTax", out DocumentField? totalTaxField))
                {
                    if (totalTaxField.ValueType == DocumentFieldType.Double)
                    {
                        double totalTax = totalTaxField.AsDouble();
                        Console.WriteLine($"Total Tax: '{totalTax}', with confidence {totalTaxField.Confidence}");
                    }
                }

                if (document.Fields.TryGetValue("InvoiceTotal", out DocumentField? invoiceTotalField))
                {
                    if (invoiceTotalField.ValueType == DocumentFieldType.Double)
                    {
                        double invoiceTotal = invoiceTotalField.AsDouble();
                        Console.WriteLine($"Invoice Total: '{invoiceTotal}', with confidence {invoiceTotalField.Confidence}");
                    }
                }
            }
            Console.WriteLine("Invoice processed successfully. Hit any key to continue");
            var input = Console.ReadLine();
        }

        public static async void AnalyzeDocument()
        {

        }

        public static async Task BuildNeuralModel(DocumentModelAdministrationClient admin)
        {
            string trainingData = "SAS URL to container";
            BuildModelOptions options = new BuildModelOptions();
            options.Prefix = "Legal-v2/";
            options.Tags.Add("CreatedBy", "CS-SDK");
            BuildModelOperation res = admin.StartBuildModel(new Uri(trainingData), DocumentBuildMode.Neural, "legal-cs3", options);
            Console.WriteLine($"Training operation {res.Id} submitted with completion status {res.HasCompleted}");
            Console.WriteLine("Initiated model training");
            // Use only with Template models
            //while (!res.HasCompleted)
            //{
            //    res.UpdateStatus();
            //    Thread.Sleep(5000);
            //}
            var input = Console.ReadLine();
        }
        public static async Task AnalyzeCustomModel(DocumentAnalysisClient client)
        {
            string pathSource = @"C:\Users\vikurpad\Desktop\FormRecognizer\Demo Data\Legal\Legal(21)-filled_07.pdf";
            string modelId = "Legal_doc_model";

            try
            {

                using (FileStream fsSource = new FileStream(pathSource,
                    FileMode.Open, FileAccess.Read))
                {
                    AnalyzeDocumentOperation result = await client.StartAnalyzeDocumentAsync(modelId, fsSource);
                    while (!result.HasCompleted)
                    {
                        Thread.Sleep(5000);
                        result.UpdateStatus();

                    }
                    foreach (AnalyzedDocument doc in result.Value.Documents)
                    {
                        Console.WriteLine($"Analyzed document of type {doc.DocType}");
                        foreach (KeyValuePair<string, DocumentField> kvp in doc.Fields)
                        {
                            Console.WriteLine($"Field {kvp.Key}: {kvp.Value.Content}");
                        }
                    }
                    Console.WriteLine(result.Value.Documents);
                }
            }
            catch (FileNotFoundException ioEx)
            {
                Console.WriteLine(ioEx.Message);
            }


        }
    }
}
