import json
import os
import sys

import boto3
from dotenv import load_dotenv
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_community.vectorstores.opensearch_vector_search import (
    OpenSearchVectorSearch,
)
from loguru import logger
from opensearchpy import OpenSearch
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
RAG_THRESHOLD = float(os.environ.get("RAG_THRESHOLD", 0.5))


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


def create_langchain_vector_embedding_using_bedrock(
    bedrock_client, bedrock_embedding_model_id
):
    bedrock_embeddings_client = BedrockEmbeddings(
        client=bedrock_client, model_id=bedrock_embedding_model_id
    )
    return bedrock_embeddings_client


def get_opensearch_client(cluster_url, username, password):
    client = OpenSearch(
        hosts=[cluster_url], http_auth=(username, password), verify_certs=True
    )
    return client


def create_opensearch_vector_search_client(
    index_name,
    bedrock_embeddings_client,
    opensearch_endpoint=OPENSEARCH_ENDPOINT,
    opensearch_username=OPENSEARCH_USERNAME,
    opensearch_password=OPENSEARCH_PASSWORD,
    _is_aoss=False,
):
    docsearch = OpenSearchVectorSearch(
        index_name=index_name,
        embedding_function=bedrock_embeddings_client,
        opensearch_url=opensearch_endpoint,
        http_auth=(opensearch_username, opensearch_password),
        is_aoss=_is_aoss,
    )
    return docsearch


def create_index(opensearch_client, index_name):
    settings = {"settings": {"index": {"knn": True, "knn.space_type": "cosinesimil"}}}
    response = opensearch_client.indices.create(index=index_name, body=settings)
    return bool(response["acknowledged"])


def create_index_mapping(opensearch_client, index_name):
    response = opensearch_client.indices.put_mapping(
        index=index_name,
        body={
            "properties": {
                "vector_field": {"type": "knn_vector", "dimension": 1536},
                "text": {"type": "keyword"},
            }
        },
    )
    return bool(response["acknowledged"])


def delete_opensearch_index(opensearch_client, index_name):
    logger.info(f"Trying to delete index {index_name}")
    try:
        response = opensearch_client.indices.delete(index=index_name)
        logger.info(f"Index {index_name} deleted")
        return response["acknowledged"]
    except Exception as e:
        logger.info(f"Index {index_name} not found, nothing to delete")
        return True


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
    index_name = event.get("index", "shiun")
    region = event.get("region", "us-east-1")
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
    bedrock_embeddings_client = create_langchain_vector_embedding_using_bedrock(
        bedrock_client, bedrock_embedding_model_id
    )
    opensearch_client = get_opensearch_client(
        OPENSEARCH_ENDPOINT, OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD
    )
    opensearch_vector_search_client = create_opensearch_vector_search_client(
        index_name,
        bedrock_embeddings_client,
        OPENSEARCH_ENDPOINT,
        OPENSEARCH_USERNAME,
        OPENSEARCH_PASSWORD,
    )

    # LangChain prompt template
    prompt = ChatPromptTemplate.from_template(
        """If the context is not relevant, please answer the question by using your own knowledge about the topic. If you don't know the answer, just say that you don't know, don't try to make up an answer. don't include harmful content

    {context}

    Question: {input}
    Answer:"""
    )

    docs_chain = create_stuff_documents_chain(bedrock_llm, prompt)
    retrieval_chain = create_retrieval_chain(
        retriever=opensearch_vector_search_client.as_retriever(),
        combine_docs_chain=docs_chain,
    )

    logger.info(
        f"Invoking the chain with KNN similarity using OpenSearch, Bedrock FM {bedrock_model_id}, and Bedrock embeddings with {bedrock_embedding_model_id}"
    )
    response = retrieval_chain.invoke({"input": question})

    source_documents = response.get("context")
    for d in source_documents:
        logger.info(f"Text: {d.page_content}")

    answer = response.get("answer")
    logger.info(f"The answer from Bedrock {bedrock_model_id} is: {answer}")

    return {"statusCode": 200, "body": answer}
