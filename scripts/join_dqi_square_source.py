#!/usr/bin/env python3
"""Experiment 012: join source qubit lifetimes with indexed Q-squared row stages.

Requires Experiment 011's actual allocator receipt, NOT a guessed physical
register layout. A physical q.id may have many source allocation generations.
Each unique physical slot contributes exactly one canonical square row.

When native helper scratch slots have no source-visible allocation witness,
retain that gap explicitly. No actual circuit optimization is performed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from constructive_qubit_square import construct_rows


def join_source_to_square(receipt: dict) -> dict:
    Q = int(receipt["num_qubits_compiled"])
    if Q < 0:
        raise ValueError("negative scored qubit count")
    by_slot: dict[int,list[dict]] = defaultdict(list)
    for event_index, event in enumerate(receipt["explicit_events"]):
        if event["kind"] == "release":
            continue
        slots = event.get("physical_slots", [])
        occurrence_ids = event.get("source_occurrences", [])
        if len(slots) != len(occurrence_ids):
            raise ValueError(f"incorrect source occurrence alignment at event {event_index}")
        for slot, occurrence in zip(slots, occurrence_ids):
            if not isinstance(slot,int) or not 0 <= slot < Q:
                raise ValueError(f"invalid physical slot {slot!r} at event {event_index}")
            by_slot[slot].append({
                "allocation_event_index":event_index,
                "source_occurrence":occurrence,
                "source_stage":event.get("stage", []),
                "source_producer":event.get("kind"),
                "source_label":event.get("label"),
            })
    rows = construct_rows(Q)
    if sum(x["new_positions"] for x in rows) != Q * Q:
        raise AssertionError("square ledger lost cells")

    result_rows=[]
    for slot_id,row in enumerate(rows):
        generations=by_slot.get(slot_id,[])
        result_rows.append({
            "physical_slot_id":slot_id,
            "accounting_index":slot_id + 1,
            "new_square_positions":row["new_positions"],
            "row_source":row["row_source"],
            "column_source":row["column_source"],
            "corner_source":row["corner_source"],
            "cumulative_square_positions":row["cumulative_positions"],
            "observed_source_allocation_count":len(generations),
            "source_allocation_status":"observed" if generations else "native_or_unobserved",
            "source_generations":generations,
        })
    return {
        "experiment":"012",
        "source_experiment":receipt.get("experiment","unknown"),
        "DQI_parameters":{k:receipt[k] for k in ("n","m","degree") if k in receipt},
        "scored_Q":Q,
        "square_factor":sum(x["new_square_positions"] for x in result_rows),
        "one_qubit_marginal_if_validly_recompiled":2*Q-1 if Q else 0,
        "rows_with_observed_source_occurrences":sum(bool(x["source_generations"]) for x in result_rows),
        "rows_without_observed_source_occurrences":sum(not bool(x["source_generations"]) for x in result_rows),
        "slots_reused_by_source":sum(len(x["source_generations"])>1 for x in result_rows),
        "indexed_rows":result_rows,
        "source_scope":(
            "The row label is a reproducible accounting index of physical q.id, "
            "not an assertion about physical geometric adjacency or causal priority. "
            "Native helper scratch may have unobserved source births."
        ),
        "optimization_status":"NO Q REDUCTION; NO OFFICIAL DQI PHASE TEST",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source_ledger",type=Path)
    p.add_argument("--report",type=Path,default=Path("/tmp/vqcc_dqi012_square_source.json"))
    args=p.parse_args()
    if args.report.exists():
        p.error("refusing to overwrite output report")
    source=json.loads(args.source_ledger.read_text(encoding="utf-8"))
    result=join_source_to_square(source)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="indexed_rows"},indent=2))
    print(f"Indexed {len(result['indexed_rows'])} physical rows at {args.report}")


if __name__=="__main__":
    main()
