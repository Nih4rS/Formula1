from __future__ import annotations
import json
from pathlib import Path


def build_indexes(data_root: Path) -> None:
    years = sorted([p.name for p in data_root.iterdir() if p.is_dir()])
    # top-level index
    (data_root / 'index.json').write_text(json.dumps({"years": years}), encoding='utf-8')

    for y in years:
        ydir = data_root / y
        events = sorted([p.name for p in ydir.iterdir() if p.is_dir()])
        (ydir / 'events.json').write_text(json.dumps(events), encoding='utf-8')
        for ev in events:
            edir = ydir / ev
            sessions = sorted([p.name for p in edir.iterdir() if p.is_dir()])
            (edir / 'sessions.json').write_text(json.dumps(sessions), encoding='utf-8')
            for ss in sessions:
                sdir = edir / ss
                drivers = sorted([p.name.split('_')[0] for p in sdir.glob('*_bestlap.json')])
                (sdir / 'drivers.json').write_text(json.dumps(drivers), encoding='utf-8')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1] / 'data'
    root.mkdir(exist_ok=True)
    build_indexes(root)

