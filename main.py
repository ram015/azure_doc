import openai
import requests
import streamlit as st
from azure.cosmos import CosmosClient

openai.api_key = "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"
url = 'https://api.openai.com/v1/chat/completions'
# Initialize Cosmos DB client (replace with your actual endpoint and key)
endpoint = "https://doc-retrival-master.documents.azure.com:443/"
key = "tOd8C7PCpTM83SvmvjAeqWPWQVHrxPi3oV0u4nXE7ja60xFxeIwiNRgfsnh6K7X1M4T33rpvvu78ACDbyqbkqQ=="
client = CosmosClient(endpoint, key)

# Create or get database and container
database_name = "master"
container_name = "db"
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)


# Function to insert master document into Cosmos DB
def insert_master_document(master_doc):
    # Read master document contents
    file_content = master_doc.getvalue().decode("utf-8")

    # Insert master document into Cosmos DB
    container.upsert_item({
        "id": "master_document",
        "content": file_content
    })


def get_master_document_content():
    query = f"SELECT * FROM c WHERE c.id = 'master_document'"
    result = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    if result:
        master_doc_item = result[0]
        return master_doc_item['content']
    else:
        st.error("Master document not found in the database.")
        return None


# Function to correct subsidiary documents based on master document
def correct_documents(subsidiary_docs, master_doc_content):
    corrected_docs = []
    for i, doc in enumerate(subsidiary_docs):
        corrected_content = apply_corrections(doc.getvalue(), master_doc_content)
        corrected_docs.append(corrected_content)
    return corrected_docs


# Function to apply corrections using OpenAI's API

headers = {

    'Authorization': f'Bearer {openai.api_key}',

    'Content-Type': 'application/json',

}


def apply_corrections(subsidiary_doc_content, context_message):
    # Convert bytes to string
    subsidiary_text = subsidiary_doc_content.decode("utf-8")

    # Call OpenAI's API to correct the text
    response = requests.post(url, headers=headers, json={
        "model": "gpt-3.5-turbo",  # Specifying GPT-4 model
        "messages": [
            {"role": "system", "content": context_message},
            {"role": "user", "content": subsidiary_text},
        ]
    })

    # Check if the request was successful
    if response.status_code == 200:
        # Parsing the response
        result = response.json()
        # Get the corrected text from the API response
        corrected_text = result['choices'][0]['message']['content'].strip()
        return corrected_text
    else:
        print(f"Failed to generate text. Status code: {response.status_code}, Message: {response.text}")
        return None


def main():
    st.title("eSolutions Pharmaceutical document Corrections tool ")
    # Check if the master document exists in Cosmos DB
    master_doc_content = get_master_document_content()
    if master_doc_content:
        st.write("Master document already uploaded.")
    else:
        # Upload master document
        st.header("Upload Master Document")
        master_doc = st.file_uploader("Upload your master document (TXT)", type=["txt"])
        if master_doc:
            st.write("Master document uploaded successfully!")
            # Call the insert_master_document function
            insert_master_document(master_doc)
    # Proceed with subsidiary document correction
    st.header("Upload Subsidiary Documents")
    uploaded_docs = st.file_uploader("Upload subsidiary documents (TXT)", type=["txt"], accept_multiple_files=True)
    if uploaded_docs:
        st.write("Subsidiary documents uploaded successfully!")
        if master_doc_content:
            # Process subsidiary documents and identify corrections
            corrected_docs = correct_documents(uploaded_docs, master_doc_content)
            if corrected_docs:
                st.subheader("Corrected Documents")
                for i, doc in enumerate(corrected_docs):
                    st.write(f"Corrected Document {i + 1}")
                    # Decode the corrected document content if it's bytes
                    if isinstance(doc, bytes):
                        doc = doc.decode("utf-8")
                    # Display the corrected document
                    st.text(doc)
                    # Generate downloadable link for the corrected document
                    download_link = f"Download Corrected Document {i + 1}"
                    st.download_button(label=download_link, data=doc.encode("utf-8"),
                                       file_name=f"corrected_document_{i + 1}.txt")


if __name__ == '__main__':
    main()
