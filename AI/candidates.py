# ai/candidates.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set, Optional
import itertools
import torch

from uni_thesis.models import ThesisDefenceRequest  # adjust app label
from AI.data_training import fetch_professor_views, compute_field_index_map, ProfView, build_training_tensors_from_db
from AI.model import train_tiny_model, predict_probs

@dataclass
class Candidate:
    id1: int
    id2: int
    features: List[float]    # [t1, t2, common_count, field_index]
    common_slots: List[str]  # for suggested_time

def build_candidates_for_field(field_value: str, exclude_ids: Set[int]) -> Tuple[List[Candidate], Dict[int, ProfView], Dict[str, int]]:
    """
    Collect eligible professors for a given field, return all overlapping pairs as candidates.
    """
    profs = fetch_professor_views()
    field_idx = compute_field_index_map(profs)

    eligible = [p for p in profs if p.field == field_value and p.id not in exclude_ids]
    if len(eligible) < 2:
        return [], {p.id: p for p in eligible}, field_idx

    candidates: List[Candidate] = []
    for p1, p2 in itertools.combinations(eligible, 2):
        common = p1.slots & p2.slots
        if not common:
            continue
        feat = [float(p1.theses), float(p2.theses), float(len(common)), float(field_idx[field_value])]
        candidates.append(Candidate(id1=p1.id, id2=p2.id, features=feat, common_slots=sorted(common)))

    return candidates, {p.id: p for p in eligible}, field_idx

def choose_best_pair_fallback(cands: List[Candidate]) -> Optional[Candidate]:
    """
    Fallback when no model/training data:
      1) maximize common_count
      2) tie-break: minimize average theses
    """
    if not cands:
        return None
    return max(
        cands,
        key=lambda c: (
            int(c.features[2]),                               # common_count (bigger is better)
            -((c.features[0] + c.features[1]) / 2.0),        # lower avg theses preferred
        )
    )

def suggest_committee_for_request(req: ThesisDefenceRequest, *, supervisor_id: Optional[int] = None) -> Dict[str, object]:
    """
    Returns a suggestion without writing to DB:
      { "status": "success" | "no_pairs" | "no_overlap" | "model_unavailable",
        "data": { evaluator_id, observer_id, score, suggested_time }? }
    """
    # 1) Resolve field (adjust this if your schema stores it elsewhere)
    field_value = getattr(req, "field_of_study", None) \
        or getattr(getattr(req, "student", None), "field_of_study", None)
    if not field_value:
        return {"status": "no_pairs", "message": "Cannot infer field_of_study from request/student."}

    # 2) Build candidates
    exclude = {supervisor_id} if supervisor_id else set()
    cands, id2prof, _ = build_candidates_for_field(field_value, exclude)

    if not id2prof or len(id2prof) < 2:
        return {"status": "no_pairs", "message": "Fewer than two eligible professors in this field."}
    if not cands:
        return {"status": "no_overlap", "message": "No professor pairs share a common time slot."}

    # 3) Train tiny model (best-effort) from DB
    X, y = build_training_tensors_from_db()
    model = train_tiny_model(X, y) if X.shape[0] > 0 else None

    # 4) Score or fallback
    if model:
        X_new = torch.tensor([c.features for c in cands], dtype=torch.float32)
        probs = predict_probs(model, X_new).squeeze(1).tolist()  # (M,)
        best_idx = int(max(range(len(cands)), key=lambda i: probs[i]))
        best = cands[best_idx]
        return {
            "status": "success",
            "data": {
                "evaluator_id": best.id1,
                "observer_id": best.id2,
                "score": float(probs[best_idx]),
                "suggested_time": best.common_slots[0] if best.common_slots else None,
            },
        }

    # Fallback path
    best = choose_best_pair_fallback(cands)
    if not best:
        return {"status": "no_overlap", "message": "No pairs with common availability."}
    return {
        "status": "model_unavailable",
        "data": {
            "evaluator_id": best.id1,
            "observer_id": best.id2,
            "score": None,
            "suggested_time": best.common_slots[0] if best.common_slots else None,
        },
    }
