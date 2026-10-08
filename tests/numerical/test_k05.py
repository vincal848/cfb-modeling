from cfb.evaluation.k05 import FAMILIES, gate, settled_events


def test_settled_events_skip_open_and_unresolved():
    ms = [{"event_ticker": "S-A", "status": "finalized", "result": "yes"}, {"event_ticker": "S-B", "status": "active", "result": ""},
          {"event_ticker": "S-C", "status": "finalized", "result": ""}]
    assert settled_events(ms) == {"A"}


def test_gate_needs_overlap_not_family_size():
    ev = {s: {str(i) for i in range(1000)} for s in FAMILIES}
    ev["KXNCAAF1HTOTAL"] = {str(i) for i in range(2000, 2300)}  # 1H events do not overlap the full-game ones
    assert gate(ev)["verdict"] == "POWERED"  # 2H and team totals still overlap fully
    ev["KXNCAAFTEAMTOTAL"] = set()
    ev["KXNCAAF2HTOTAL"] = set()
    assert gate(ev)["verdict"] == "UNDERPOWERED, NOT RUN"
