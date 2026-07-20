# from sqlalchemy.orm import Session
from app.models.metadata_models import Dataset
from typing import List, Optional
from datetime import datetime
from app.db.postgres import session_scope




def create_dataset_entry(
    username: str,
    question: str,
    ground_truth_chunk_ids: List[str],
    document_id: Optional[str] = None,
    ground_truth_document_ids: Optional[List[str]] = None,
    metadata_info: Optional[dict] = None,
):
    
    try:
        with session_scope() as session:
            session.add(
                Dataset(
                username=username, #quick fix needed for user_id
                document_id=document_id,
                question=question,
                ground_truth_chunk_ids=ground_truth_chunk_ids,
                ground_truth_document_ids=ground_truth_document_ids,
                metadata_info=metadata_info or {},
                )
            )
    except Exception as error:
        print(f"{error}")

def get_all_datasets():
    try:
        with session_scope() as session:
            datasets = session.query(Dataset).all()
            
            return [
                {
                    "id": d.id,
                    "username": d.username,
                    "question": d.question,
                    "document_id": d.document_id,
                    "ground_truth_chunk_ids": d.ground_truth_chunk_ids,
                    "ground_truth_document_ids": d.ground_truth_document_ids,
                    "metadata_info": d.metadata_info,
                }
                for d in datasets
            ]
    except Exception as error:
        print(f"{error}")
        return []