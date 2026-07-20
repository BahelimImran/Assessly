
from app.services.dataset.dataset_service import get_all_datasets
from typing import List, Dict, Any
from rapidfuzz import process, fuzz
def ragas_row(user_question:str, context:str, answer:str):

    try:
        # Build RAGAS row
        ragas_row = {
            "question": user_question,
            "contexts": [context], # Task- top-k parent chunk content should be used 
            "answer": answer,
            "ground_truth": ground_truth_lookup(user_question)
        }

        return ragas_row
    except Exception as error:
        print(error)

def ground_truth_lookup(user_question: str) -> str:

    try:

        # Fetch GROUND_TRUTH_DB based on postgresql table dataset
        entire_dataset = get_all_datasets()
        # 1. Exact match
        gt = exact_match_lookup(user_question, entire_dataset)
        if gt:
            return gt

        # 2. Fuzzy match
        gt = fuzzy_lookup(user_question, entire_dataset)
        if gt:
            return gt

        # 3. Semantic-Retrieval-based
        # gt = semantic_retrieval_lookup(user_question)
        # if gt:
        #     return gt

        # # 4. Optional LLM fallback (last resort)
        # return llm.generate(
        #     f"Provide a correct factual answer for evaluation:\nQuestion: {query}"
        # )

    except Exception as error:
        print(error)





def normalize_query(query: str) -> str:
    try:
        return query.strip().lower()
    
    except Exception as error:
        print(error)

def exact_match_lookup(user_question:str, entire_dataset:List[Dict[str, Any]]):

    try:
        normalized = normalize_query(user_question)
    
        if normalized in entire_dataset:
            return entire_dataset[normalized]
        
        return None  # or fallback
    
    except Exception as error:
        print(error)



def fuzzy_lookup(user_question: str, entire_dataset: List[Dict[str, Any]]):

    try:
        # Extract questions (or whichever field you want)
        questions = [item["question"] for item in entire_dataset]

        match, score, idx = process.extractOne(
            user_question,
            questions,
            scorer=fuzz.token_sort_ratio
        )

        if score > 80:
            return questions[idx] #entire_dataset[idx]

        print(f"No strong match for query: {user_question} (score={score})")
        return None

    except Exception as error:
        print(error)