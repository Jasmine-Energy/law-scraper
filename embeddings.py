
import pandas as pd
import glob
import pickle

from os import path
from openai import OpenAI

import torch

from transformers import AutoTokenizer, AutoModel


client = OpenAI()

def get_embedding(text, model="text-embedding-ada-002"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding


def read_texts():

    texts, metadatas, results, file_names = [], [], [], []
    for file_path in glob.glob('data/*.txt'):

        file_name, _ = path.splitext(path.basename(file_path))
        metadata = dict(param.split('=') for param in file_name.split('&'))
        print(metadata)

        with open(file_path) as file:
            text = file.read()
            if len(text) > 25000:
                print(f'Skipping: {file_path}')
                continue
            metadata['text'] = text
            file_names.append(file_name)
            texts.append(text)
            metadatas.append(metadata)
            results.append(metadata)

    return file_names, results


file_names, results = read_texts()
df = pd.DataFrame.from_records(results, index=file_names)
# df['embedding'] = df.text.apply(lambda x: get_embedding(x, model='text-embedding-ada-002'))
# df.to_csv('output/embedded_1k_reviews.csv', index=False)


# Load tokenizer and model
model_name = 'bert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

def get_embedding(text):
    """
    Gets the embedding for a text string using a Hugging Face transformer model.

    Args:
        text (str): The input text.
        model_name (str, optional): The name of the Hugging Face model. 
                                   Defaults to "bert-base-uncased".

    Returns:
        torch.Tensor: The embedding as a PyTorch tensor.
    """

    # Tokenize input text
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)

    # Get model output (hidden states)
    with torch.no_grad():  # No need to track gradients for inference
        outputs = model(**inputs)

    # Choose a suitable embedding representation (e.g., last hidden state, mean pooling)
    # Here, we'll use the last hidden state of the [CLS] token as the embedding
    embedding = outputs.last_hidden_state[:, 0, :]  # [CLS] token embedding

    return embedding

df['embedding'] = df.text.apply(get_embedding)

with open('bert_embedded.pkl', 'wb') as file:
    pickle.dump(df, file)