from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset
from app.services.evaluation.evaluation_match import ragas_row

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from app.core.config import *


llm = ChatOllama(
    model=ANSWER_VERIFICATION_LLM_MODEL,   # or mistral, etc.
    temperature=0
)

embeddings = OllamaEmbeddings(
    model=EMBED_MODEL   # or any embedding model you have
)

def ragas_evaluation(user_question:str, context:str, answer:str):

    try:
        row_ragas = ragas_row(user_question, context, answer)
        # Convert to dataset
        dataset = Dataset.from_list([row_ragas])

        # Run evaluation
        results = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                # context_precision,
                # context_recall
            ],
            llm=llm,               
            embeddings=embeddings
        )

        return results
    
    except Exception as error:
        print(error)


