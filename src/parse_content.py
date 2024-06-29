import os
import json
from urllib3 import request
from bs4 import BeautifulSoup
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


def extract_metadata(content: dict) -> dict:
    html_summary = BeautifulSoup(content["summary"], "html.parser") if content["summary"] else None
    summary = html_summary.get_text() if html_summary else "N/A"
    summary_links = [link.get("href") for link in html_summary.find_all("a") if link.get("href")] if html_summary else []
    metadata = {
        "name": content["name"],
        "category": content["typeObj"]["categoryObj"]["name"],
        "type": content["typeObj"]["name"],
        "sector": content["sectorObj"]["name"],
        "source": content["websiteUrl"] or "N/A",
        "summary": summary.replace("\n", " ").replace("\t", " ").strip(),
        "summary_links": summary_links,
    }
    if metadata["sector"] == "State" or metadata["sector"] == "Local":
        metadata["state"] = content["stateObj"]["abbreviation"]
    if metadata["sector"] == "Local":
        metadata["county"] = content["name"].split("-")[0].strip()
    return metadata


def generate_embedding(text: str) -> list:
    embedding = (
        # TODO: Batch requests
        openai_client.embeddings.create(input=[text], model=EMBED_MODEL)
        .data[0]
        .embedding
    )
    return embedding


def fetch_batch(start: int, length: int = 100):
    url = f"https://programs.dsireusa.org/api/v1/programs?draw=1&columns%5B0%5D%5Bdata%5D=name&columns%5B0%5D%5Bname%5D&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=stateObj.abbreviation&columns%5B1%5D%5Bname%5D&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=categoryObj.name&columns%5B2%5D%5Bname%5D&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=typeObj.name&columns%5B3%5D%5Bname%5D&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=published&columns%5B4%5D%5Bname%5D&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=createdTs&columns%5B5%5D%5Bname%5D&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=updatedTs&columns%5B6%5D%5Bname%5D&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=6&order%5B0%5D%5Bdir%5D=desc&start={start}&length={length}&search%5Bvalue%5D&search%5Bregex%5D=false"
    content = fetch_content(url)
    for entry in content["data"]:
        parsed = extract_metadata(entry)
        embedding = generate_embedding(json.dumps(entry))
        yield (
            str(entry["id"]),
            embedding,
            parsed,
        )


start_index = 0
end_index = 2_543
page_count = 100


while start_index < end_index:
    if start_index + page_count > end_index:
        page_count = end_index - start_index

    content = fetch_batch(start_index, page_count)

    batches = []
    for entry in content:
        batches.append(entry)

    index.upsert(
        vectors=batches,
    )
    start_index += page_count
    print(f"Processed {start_index} entries")
