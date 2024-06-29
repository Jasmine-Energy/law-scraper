import os
import json
from urllib3 import request
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBEDDING_DIM = 1536  # dimensionality of text-embedding-ada-002
EMBED_MODEL = "text-embedding-ada-002"
index_name = "dsire-programs"
cloud = os.environ.get("PINECONE_CLOUD") or "aws"
region = os.environ.get("PINECONE_REGION") or "us-east-1"

spec = ServerlessSpec(cloud=cloud, region=region)

pinecone = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
)


if index_name not in pinecone.list_indexes().names():
    pinecone.create_index(index_name, dimension=1536, metric="cosine", spec=spec)

index = pinecone.Index(index_name)
index.describe_index_stats()


def fetch_content(url: str) -> str:
    response = request("GET", url)
    return json.loads(response.data)


def format_content(content: dict) -> str:
    name = content["name"]
    summary = content["summary"]
    category = content["typeObj"]["categoryObj"]["name"]
    type = content["typeObj"]["name"]
    state = content["stateObj"]["abbreviation"]
    source = content["websiteUrl"]
    return f"Name: `{name}` Summary: `{summary}` Category: `{category} - {type}` State: `{state}` Source: {source}"


def generate_embedding(text: str) -> list:
    embedding = (
        openai_client.embeddings.create(input=[text], model=EMBED_MODEL)
        .data[0]
        .embedding
    )
    return embedding

start_index = 0
end_index = 2_543
page_count = 100


while start_index < end_index:
    if start_index + page_count > end_index:
        page_count = end_index - start_index

    content = fetch_content(
        f"https://programs.dsireusa.org/api/v1/programs?draw=1&columns%5B0%5D%5Bdata%5D=name&columns%5B0%5D%5Bname%5D&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=stateObj.abbreviation&columns%5B1%5D%5Bname%5D&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=categoryObj.name&columns%5B2%5D%5Bname%5D&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=typeObj.name&columns%5B3%5D%5Bname%5D&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=published&columns%5B4%5D%5Bname%5D&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=createdTs&columns%5B5%5D%5Bname%5D&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=updatedTs&columns%5B6%5D%5Bname%5D&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=6&order%5B0%5D%5Bdir%5D=desc&start={start_index}&length={page_count}&search%5Bvalue%5D&search%5Bregex%5D=false"
    )

    batches = []
    for entry in content["data"]:
        formatted = format_content(entry)
        name = entry["name"] or "N/A"
        summary = entry["summary"] or "N/A"
        category = entry["typeObj"]["categoryObj"]["name"] or "N/A"
        type = entry["typeObj"]["name"] or "N/A"
        state = entry["stateObj"]["abbreviation"] or "N/A"
        source = entry["websiteUrl"] or "N/A"
        embedding = generate_embedding(formatted)
        batches.append(
            (
                str(entry["id"]),
                embedding,
                {
                    "state": state,
                    "name": name,
                    "category": category,
                    "type": type,
                    "source": source,
                    "summary": summary,
                },
            )
        )

    index.upsert(
        vectors=batches,
    )
    start_index += page_count
    print(f"Processed {start_index} entries")
