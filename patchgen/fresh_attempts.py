"""Append-only fresh-screen reservations, recorded before credentials or requests."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1]/'fresh-screen/attempts.jsonl'


def begin(output, backend, model, strategy, sample, manifest_sha256, rerun_reason=None, *, path=None):
    if type(sample) is not int or sample < 1:
        raise ValueError('--fresh requires --sample N (1-based)')
    if rerun_reason is not None and not rerun_reason.strip():
        raise ValueError('--rerun-reason must be nonempty')
    path = Path(path) if path is not None else DEFAULT
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('fresh attempts ledger must not be a symlink')
    with path.open('a+') as ledger:
        fcntl.flock(ledger, fcntl.LOCK_EX)
        ledger.seek(0)
        rows = [json.loads(line) for line in ledger if line.strip()]
        previous = [row for row in rows if (row['model'], row['strategy'], row['sample']) == (model, strategy, sample)]
        if previous and not rerun_reason:
            raise ValueError('fresh model/strategy/sample already attempted; use --rerun-reason for a flagged, non-substituting rerun')
        row = dict(attempt=len(rows)+1, timestamp=datetime.now(timezone.utc).isoformat(), backend=backend,
                   model=model, strategy=strategy, sample=sample, output_dir=str(Path(output).resolve()),
                   manifest_sha256=manifest_sha256, rerun=bool(previous), rerun_reason=rerun_reason,
                   original_attempt=previous[0]['attempt'] if previous else None)
        ledger.write(json.dumps(row, sort_keys=True)+'\n')
        ledger.flush()
        os.fsync(ledger.fileno())
        return row
