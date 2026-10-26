"""Offline purged walk-forward partitions; no trading claims."""
from datetime import date

def walk_forward_folds(events, boundaries, embargo_sessions=20,
                       min_train_issuers=30, min_test_issuers=15):
    if type(embargo_sessions) is not int or embargo_sessions < 0:
        raise ValueError("invalid embargo")
    if min_train_issuers < 1 or min_test_issuers < 1:
        raise ValueError("invalid minimum")
    checked, seen = [], set()
    for i, row in enumerate(events):
        try:
            issuer, episode = row["issuer_id"], row["episode_id"]
            day = date.fromisoformat(row["signal_date"])
            signal, end = row["signal_session"], row["label_end_session"]
            if (not isinstance(issuer, str) or not issuer or
                    not isinstance(episode, str) or not episode or
                    type(signal) is not int or type(end) is not int or
                    signal < 0 or end < signal):
                raise ValueError("invalid lifetime")
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid event") from exc
        if (issuer, episode) in seen:
            raise ValueError("duplicate episode")
        seen.add((issuer, episode))
        checked.append((i, issuer, day, signal, end))
    output, previous_end, previous_start_session = [], None, None
    for boundary in boundaries:
        try:
            start = date.fromisoformat(boundary["start_date"])
            stop = date.fromisoformat(boundary["end_date"])
            ordinal = boundary["start_session"]
            if type(ordinal) is not int or ordinal < 0 or start >= stop:
                raise ValueError("invalid boundary")
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid boundary") from exc
        if (previous_end is not None and
                (start < previous_end or ordinal <= previous_start_session)):
            raise ValueError("overlap or unordered fold")
        previous_end, previous_start_session = stop, ordinal
        test = [i for i, issuer, day, s, end in checked if start <= day < stop]
        if any(s < ordinal for i, issuer, day, s, end in checked if start <= day < stop):
            raise ValueError("inconsistent calendar")
        train = [i for i, issuer, day, s, end in checked
                 if day < start and end < ordinal - embargo_sessions]
        ntrain = len({events[i]["issuer_id"] for i in train})
        ntest = len({events[i]["issuer_id"] for i in test})
        output.append({"start_date":str(start), "end_date":str(stop),
                       "train_indices":train, "test_indices":test,
                       "train_issuers":ntrain, "test_issuers":ntest,
                       "embargo_sessions":embargo_sessions,
                       "status":("eligible_for_offline_evaluation" if
                                 ntrain >= min_train_issuers and ntest >= min_test_issuers
                                 else "insufficient_independent_issuers"),
                       "interpretation":"partition_only_not_oos_evidence"})
    return output
