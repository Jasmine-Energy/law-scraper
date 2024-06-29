from typing import Dict

import torch
import numpy as np
from transformers import AutoModel, AutoTokenizer
from sentence_transformers.util import cos_sim


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


# For retrieval you need to pass this prompt. Please find our more in our blog post.
def transform_query(query: str) -> str:
    """ For retrieval, add the prompt for query (not for documents).
    """
    return f'Represent this sentence for searching relevant passages: {query}'


# The model works really well with cls pooling (default) but also with mean pooling.
def pooling(outputs: torch.Tensor, inputs: Dict,  strategy: str = 'cls') -> np.ndarray:
    if strategy == 'cls':
        outputs = outputs[:, 0]
    elif strategy == 'mean':
        outputs = torch.sum(
            outputs * inputs["attention_mask"][:, :, None], dim=1) / torch.sum(inputs["attention_mask"])
    else:
        raise NotImplementedError
    return outputs.detach().cpu().numpy()


# 1. load model
model_id = 'mixedbread-ai/mxbai-embed-large-v1'
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModel.from_pretrained(model_id)

docs = df['text']


# 2. encode
inputs = tokenizer(docs, padding=True, return_tensors='pt')
for k, v in inputs.items():
    inputs[k] = v
outputs = model(**inputs).last_hidden_state
embeddings = pooling(outputs, inputs, 'cls')
df['embeddings'] = embeddings

similarities = cos_sim(embeddings[0], embeddings[1:])
print('similarities:', similarities)