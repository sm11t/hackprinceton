"""Additive typed contract. Deterministic gates are never model overrides."""
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypedDict


class Evidence(TypedDict):
    fact: str
    value: Any
    source: str
    source_id: Any
    captured_at: str | None
    confidence: float | None
    evidence_url: str | None
    status: Literal['agrees', 'conflict', 'unknown']
    needs_human: bool
    note: str


@dataclass
class DecisionContext:
    property_id: int
    suite: str | None
    scope: str
    desired_use: str
    tenure: Literal['buy', 'lease']
    cash_budget: float
    evidence: list[Evidence] = field(default_factory=list)
    conflicts: list[Evidence] = field(default_factory=list)
    confidence: str = 'conditional; coverage incomplete'
    gates: dict = field(default_factory=dict)
    assumptions: dict = field(default_factory=dict)
    version: int = 1


def attach_context(report, inputs):
    # Attachment provenance is retained separately; never display it as camera capture.
    for row in report['identity']['records'] + (report.get('space') or {}).get('records', []):
        if row['source'] == 'matterport' and row.get('captured_at'):
            row['attachment_date'] = row['captured_at']
            row['captured_at'] = None
            row['note'] += ' CoStar attachment date only; actual camera capture date is unknown.'
        if row['fact'] == 'suite_occupancy_at_scan':
            row['status'] = 'unknown'
            row['needs_human'] = True
            row['note'] = 'Attachment-date tenancy comparison is a screening hypothesis, not verified occupancy at camera capture. Confirm scan date and photos. ' + row['note']
    evidence = list(report['identity']['records'])
    evidence += (report.get('space') or {}).get('records', [])
    context = DecisionContext(
        property_id=report['property_id'], suite=report['requested_suite'],
        scope=report['scope_label'], desired_use=report['proposed_use'], tenure=report['ownership'],
        cash_budget=float(inputs.get('starting_cash', 320000)), evidence=evidence,
        conflicts=[r for r in evidence if r['status'] == 'conflict'],
        gates={'eligibility': report['eligibility']['status'],
               'physical_fit': (report.get('space') or {}).get('verdict', 'not_run'),
               'permission': 'unverified', 'paid_demand': 'unverified'},
        assumptions=dict(inputs))
    report['decision_context'] = asdict(context)
    return report
