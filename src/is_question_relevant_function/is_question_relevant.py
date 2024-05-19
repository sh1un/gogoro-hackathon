import json
import os
import sys

import boto3
from chat_history import get_chat_history, write_messages_to_table
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
from opensearchpy import OpenSearch
from output_util import text_to_json
from secret import (
    get_opensearch_endpoint,
    get_opensearch_password,
    get_opensearch_username,
)

# logger
logger.remove()
logger.add(sys.stdout, level=os.getenv("LOG_LEVEL", "INFO"))


# Load environment variables from a .env file if present
load_dotenv()

AWS_PROFILE = os.environ.get("AWS_PROFILE")
INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")
AZURE_DEPLOYMENT_NAME = os.environ.get("AZURE_DEPLOYMENT_NAME")
AZURE_EMBEDDINGS_DEPLOYMENT_NAME = os.environ.get("AZURE_EMBEDDINGS_DEPLOYMENT_NAME")

# OpenSearch
OPENSEARCH_ENDPOINT = get_opensearch_endpoint()
OPENSEARCH_USERNAME = get_opensearch_username()
OPENSEARCH_PASSWORD = get_opensearch_password()
RAG_THRESHOLD = float(os.environ.get("RAG_THRESHOLD", 0.6))
EMBEDDING_DIMENSION = 1536


def get_model(model: str = "claude 3 sonnet") -> ChatBedrock:
    model = model.lower()
    if model == "claude 3 sonnet":
        llm = ChatBedrock(
            credentials_profile_name=AWS_PROFILE,
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            streaming=True,
        )
    return llm


def get_bedrock_client(region):
    bedrock_client = boto3.client("bedrock-runtime", region_name=region)
    return bedrock_client


def cal_embedding(bedrock_client, text: str) -> list:
    body = json.dumps({"inputText": text})
    modelId = "amazon.titan-embed-text-v1"
    accept = "*/*"
    contentType = "application/json"

    response = bedrock_client.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    return response_body["embedding"]


def get_opensearch_client(cluster_url, username, password):
    client = OpenSearch(
        hosts=[cluster_url], http_auth=(username, password), verify_certs=True
    )
    return client


def create_langchain_vector_embedding_using_bedrock(
    bedrock_client, bedrock_embedding_model_id
):
    bedrock_embeddings_client = BedrockEmbeddings(
        client=bedrock_client, model_id=bedrock_embedding_model_id
    )
    return bedrock_embeddings_client


def ensure_index(client, index_name, dimension):
    index_body = {
        "properties": {
            "embedding": {"type": "knn_vector", "dimension": dimension},
            "id": {"type": "integer"},
            "title": {"type": "text"},
        }
    }
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body={"mappings": index_body})
    else:
        # Update the mapping
        client.indices.put_mapping(index=index_name, body=index_body)


def retrieve_data(client, query_embedding, index_name, top_k=3):
    query_body = {
        "query": {
            "knn": {"document_embedding": {"vector": query_embedding, "k": top_k}}
        },
        "_source": False,
        "fields": ["chapter", "document"],
    }
    results = client.search(body=query_body, index=index_name)
    return results["hits"]["hits"]


def extract_and_combine_documents(results):
    combined_content = ""
    for result in results:
        fields = result.get("fields", {})
        document = fields.get("document", [""])[0]
        if document:
            combined_content += document + "\n\n"

    system_message = SystemMessage(content=combined_content.strip())
    return [system_message]


def lambda_handler(event, context):
    logger.info("Starting...")

    # Get API Gateway event body
    body = event.get("body", "")
    if body:
        payload = json.loads(body)
    else:
        payload = {}

    # Retrieve parameters from the event
    question = payload.get("input", {}).get("question", "What is the meaning of <3?")
    index_name = payload.get("input", {}).get("index", "shiun")
    session_id = payload.get("input", {}).get("session_id", "0")
    region = event.get("region", "us-west-2")
    bedrock_model_id = event.get(
        "bedrock_model_id", "anthropic.claude-3-sonnet-20240229-v1:0"
    )
    bedrock_embedding_model_id = event.get(
        "bedrock_embedding_model_id", "amazon.titan-embed-text-v1"
    )

    logger.info(f"Question provided: {question}")

    # Creating all clients for chain
    bedrock_client = get_bedrock_client(region)
    bedrock_llm = get_model()
    opensearch_client = get_opensearch_client(
        OPENSEARCH_ENDPOINT, OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD
    )

    # Ensure index
    ensure_index(opensearch_client, index_name, EMBEDDING_DIMENSION)

    # LangChain prompt template
    prompt = ChatPromptTemplate.from_template(
        """Let me break down my thought process step-by-step when answering your questions about Gogoro's products and services:

Step 1: Analyze the question and identify any missing key information.
Chat History: {chat_history}  
Question: {input}
[analyze question and chat history]

Step 2: Check if the provided context contains enough information to answer, combined with my own knowledge about Gogoro.
{context}
[check context sufficiency]

Step 3: If needed, politely request any additional information required to comprehensively answer.
[request additional info]

Step 4: For input questions, a picture in Markdown format must be output.
[output relevant images in markdown]

Step 5: Provide a step-by-step answer in the same language as the question, utilizing all available information. 
[answer steps in same language as question]

Final Answer: [result]

If I don't have enough information to answer adequately, I will admit that. I will not make up answers or include any harmful content.

Question: {input}
Answer:"""
    )

    logger.info(
        f"Invoking the chain with KNN similarity using OpenSearch, Bedrock FM {bedrock_model_id}, and Bedrock embeddings with {bedrock_embedding_model_id}"
    )
    chat_history = get_chat_history(table_name="session_table", session_id=session_id)

    # Calculate the query embedding
    query_embedding = cal_embedding(bedrock_client, question)
    logger.info(f"Query embedding: {query_embedding}")

    # Retrieve data from OpenSearch
    results = retrieve_data(opensearch_client, query_embedding, index_name, top_k=3)
    logger.info(f"Results from OpenSearch: {results}")
    relevant_docs = [hit for hit in results if hit["_score"] >= RAG_THRESHOLD]

    if not relevant_docs:
        answer = "很抱歉,這個問題超出了我的知識範圍或與 Gogoro 產品和服務無關。作為一位 Gogoro 萬事通機器人,我無法為您解答這類問題。不過,如果您有任何關於 Gogoro 智慧電動機車系列、電池交換系統或其他相關產品和服務的疑問,我將竭誠為您解答和提供協助。\n I'm sorry, but this question falls outside of my knowledge or is unrelated to Gogoro's products and services. As the Gogoro product master, I cannot provide an answer to questions of this nature. However, if you have any inquiries regarding Gogoro's Smartscooter electric scooter series, battery swapping system, or other related products and services, I would be more than happy to assist you and provide answers to the best of my abilities."
    else:
        chain = prompt | bedrock_llm | StrOutputParser()
        answer = chain.invoke(
            {
                "chat_history": chat_history,
                "context": extract_and_combine_documents(results),
                "input": question,
            }
        )
        logger.info(f"Context: {extract_and_combine_documents(results)}")

    logger.info(f"The answer from Bedrock {bedrock_model_id} is: {answer}")

    write_messages_to_table(
        question=question,
        answer=answer,
        table_name="session_table",
        session_id=session_id,
    )

    logger.info(
        f"After this invoke is done, now the history has: {get_chat_history(table_name='session_table', session_id='0')}"
    )
    return_response_body = text_to_json(answer, results)

    return {"statusCode": 200, "body": return_response_body}
