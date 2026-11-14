from datetime import date, timedelta
import pytest
from cinema_forge.quota import QuotaLedger, QuotaExceeded

D = date(2026, 11, 14)

def test_five_per_day_then_refuse(tmp_path):
    q=QuotaLedger(tmp_path/'ledger.db')
    for i in range(5):
        assert q.reserve(user_id='u1', role_from_server='user',request_key=str(i),today=D)=='reserved'
    assert q.used('u1',D)==5
    with pytest.raises(QuotaExceeded):
        q.reserve(user_id='u1',role_from_server='user',request_key='6',today=D)
    assert q.reserve(user_id='u1',role_from_server='user',request_key='6',today=D+timedelta(days=1))=='reserved'
    q.close()

def test_developer_unlimited_policy_not_compute(tmp_path):
    q=QuotaLedger(tmp_path/'ledger.db')
    for i in range(13):
        q.reserve(user_id='owner',role_from_server='developer',request_key=str(i),today=D)
    assert q.used('owner',D)==13
    with pytest.raises(ValueError):
        q.reserve(user_id='owner',role_from_server='administrator',request_key='bad',today=D)
    q.close()

def test_idempotency_completion_and_released_failures(tmp_path):
    q=QuotaLedger(tmp_path/'ledger.db',limit=1)
    assert q.reserve(user_id='u',role_from_server='user',request_key='k1',today=D)=='reserved'
    assert q.reserve(user_id='u',role_from_server='user',request_key='k1',today=D)=='reserved'
    q.finish('u','k1',False)
    assert q.used('u',D)==0
    assert q.reserve(user_id='u',role_from_server='user',request_key='k2',today=D)=='reserved'
    q.finish('u','k2',True)
    with pytest.raises(KeyError): q.finish('u','k2',True)
    with pytest.raises(QuotaExceeded):
        q.reserve(user_id='u',role_from_server='user',request_key='k3',today=D)
    q.close()

def test_user_separation(tmp_path):
    q=QuotaLedger(tmp_path/'ledger.db',limit=1)
    assert q.reserve(user_id='a',role_from_server='user',request_key='same',today=D)=='reserved'
    assert q.reserve(user_id='b',role_from_server='user',request_key='same',today=D)=='reserved'
    q.close()
