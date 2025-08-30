# ai/training_data.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set
import itertools
from django.db.models import Count, Prefetch
from django.utils.timezone import now

from uni_thesis.models import Professor, TimeSlot  # adjust app label

# ---------- Lightweight view over your ORM ----------

@dataclass
class ProfView:
    id: int
    field: str                 # Professor.field_of_study
    theses: int                # experience proxy (#sessions served)
    slots: Set[str]            # comparable time slot keys

def _slot_key(ts: TimeSlot) -> str:
    # "YYYY-MM-DD|HH:MM-HH:MM" for stable set intersections
    return f"{ts.date.isoformat()}|{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}"

def fetch_professor_views(*, only_future_slots: bool = True) -> List[ProfView]:
    """
    Load professors with:
      - theses count = evaluator_sessions + observer_sessions
      - available time slots (future only if only_future_slots=True)
    """
    ts_qs = TimeSlot.objects.filter(available=True)
    if only_future_slots:
        ts_qs = ts_qs.filter(date__gte=now().date())

    qs = (
        Professor.objects
        .annotate(
            eval_count=Count('evaluator_sessions', distinct=True),
            obs_count=Count('observer_sessions', distinct=True),
        )
        .prefetch_related(Prefetch('time_slots', queryset=ts_qs))
    )

    views: List[ProfView] = []
    for p in qs:
        theses = int((p.eval_count or 0) + (p.obs_count or 0))
        slots = {_slot_key(ts) for ts in p.time_slots.all()}
        views.append(ProfView(id=p.id, field=p.field_of_study, theses=theses, slots=slots))
    return views

def compute_field_index_map(profs: List[ProfView]) -> Dict[str, int]:
    """Map each field string to a small integer index (stable ordering)."""
    fields = sorted({p.field for p in profs})
    return {f: i for i, f in enumerate(fields)}

# ---------- Build training tensors using your heuristic ----------

def build_training_tensors_from_db() -> Tuple['torch.Tensor','torch.Tensor']:
    """
    Returns:
      X: (N, 4) float32  -> [p1_theses, p2_theses, common_count, field_index]
      y: (N, 1) float32  -> 0/1 labels by heuristic:
            avg = (p1_theses + p2_theses)/2
            label = 1 if avg <= dept_avg(field) and common_count >= 3 else 0
    """
    import torch

    profs = fetch_professor_views()
    if not profs:
        return torch.zeros((0,4), dtype=torch.float32), torch.zeros((0,1), dtype=torch.float32)

    field_idx = compute_field_index_map(profs)

    # per-field average theses
    by_field: Dict[str, List[int]] = {}
    for p in profs:
        by_field.setdefault(p.field, []).append(p.theses)
    dept_avg: Dict[str, float] = {f: (sum(vals)/max(len(vals),1)) for f, vals in by_field.items()}

    # build pairs within each field
    samples: List[List[float]] = []
    labels:  List[List[float]] = []
    grouped: Dict[str, List[ProfView]] = {}
    for p in profs:
        grouped.setdefault(p.field, []).append(p)

    for f, group in grouped.items():
        if len(group) < 2:
            continue
        davg = float(dept_avg[f])
        for p1, p2 in itertools.combinations(group, 2):
            common = p1.slots & p2.slots
            if not common:
                continue
            common_count = len(common)
            avg = (p1.theses + p2.theses) / 2.0
            label = 1.0 if (avg <= davg and common_count >= 3) else 0.0
            samples.append([float(p1.theses), float(p2.theses), float(common_count), float(field_idx[f])])
            labels.append([label])

    if not samples:
        return torch.zeros((0,4), dtype=torch.float32), torch.zeros((0,1), dtype=torch.float32)

    X = torch.tensor(samples, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.float32)
    return X, y
