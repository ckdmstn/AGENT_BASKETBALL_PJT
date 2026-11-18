"""Offline contract tests. HTTP responses here are synthetic, not live evidence."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.config import Settings
from backend.main import app
from backend.schemas import SearchGamesInput, ToolFailure, ToolSuccess
from backend.tools.registry import TOOLS, invoke, tool_specs
from backend.tools.weather import grid_coordinates, forecast_base


def response(body, status=200):
    value = Mock(status_code=status)
    value.json.return_value = body
    return value


def settings(**kwargs):
    return Settings(**kwargs)


def test_health_and_docs():
    client = TestClient(app)
    assert client.get('/api/health').json() == {'status': 'ok'}
    assert client.get('/docs').status_code == 200
    assert '/api/health' in client.get('/openapi.json').json()['paths']


def test_registry_has_four_external_typed_tools():
    specs = tool_specs()
    assert set(TOOLS) == {'search_kbl_games', 'get_kbl_game_detail', 'search_arena', 'get_weather'}
    assert all(s['kind'] == 'external' and s['description'] for s in specs)
    assert all(s['input_schema'] and s['output_schema'] for s in specs)


def test_date_range_rejected():
    with pytest.raises(ValidationError):
        SearchGamesInput(from_date='2026-11-20', to_date='2026-11-18')


@pytest.mark.parametrize('tool,args', [
    ('search_arena', {'venue_name': '잠실학생체육관'}),
    ('get_weather', {'date_time': '2026-11-18T18:00:00+09:00', 'lat': 37.5, 'lon': 127.0}),
])
def test_missing_keys_never_calls_http(tool, args):
    with patch('requests.get') as get:
        result = invoke(tool, args, settings())
    assert not result.ok and result.error.code == 'MISSING_API_KEY'
    get.assert_not_called()


def test_invalid_input_and_unknown_tool_are_safe():
    for tool, args in [('search_arena', {'venue_name': ''}), ('unknown', {})]:
        assert invoke(tool, args, settings()).error.code == 'INVALID_INPUT'


def test_kakao_mock_success_preserves_candidates_without_verification():
    body = {'documents': [{'place_name': '체육관', 'road_address_name': '서울 도로',
                           'address_name': '서울', 'y': '37.5', 'x': '127.0',
                           'place_url': 'https://place.map.kakao.com/1'}]}
    with patch('requests.get', return_value=response(body)):
        result = invoke('search_arena', {'venue_name': '체육관'}, settings(kakao_key='secret'))
    assert result.ok and result.data[0].lat == 37.5
    assert result.data[0].verified_kbl_arena is False
    assert 'secret' not in result.model_dump_json()


@pytest.mark.parametrize('body,code', [({'documents': []}, 'NO_RESULT'), ({}, 'MISSING_FIELD'),
                                       ({'documents': 'bad'}, 'MISSING_FIELD')])
def test_kakao_empty_and_changed_response(body, code):
    with patch('requests.get', return_value=response(body)):
        result = invoke('search_arena', {'venue_name': '체육관'}, settings(kakao_key='secret'))
    assert result.error.code == code


@pytest.mark.parametrize('error,code', [(requests.Timeout('secret'), 'TIMEOUT'),
                                       (requests.ConnectionError('secret'), 'UPSTREAM_ERROR')])
def test_network_errors_do_not_expose_exception(error, code):
    with patch('requests.get', side_effect=error):
        result = invoke('search_arena', {'venue_name': '체육관'}, settings(kakao_key='secret'))
    assert result.error.code == code
    assert 'secret' not in result.model_dump_json()


def test_http_error_and_non_json():
    for resp in [response({'message': 'secret'}, 401), response(None)]:
        if resp.status_code == 200:
            resp.json.side_effect = ValueError('secret')
        with patch('requests.get', return_value=resp):
            result = invoke('search_arena', {'venue_name': '체육관'}, settings(kakao_key='secret'))
        assert result.error.code == 'UPSTREAM_ERROR'
        assert 'secret' not in result.model_dump_json()


def test_http_error_retains_service_code_without_server_message():
    with patch('requests.get', return_value=response({'resultCode': 'Fail', 'message': 'secret'}, 500)):
        result = invoke('search_kbl_games', {'from_date': '2026-11-18', 'to_date': '2026-11-18'}, settings())
    assert result.meta.http_status == 500 and result.meta.service_code == 'Fail'
    assert 'secret' not in result.model_dump_json()


def test_settings_repr_hides_credentials():
    assert 'hidden-value' not in repr(settings(kakao_key='hidden-value', kma_key='hidden-value'))


@pytest.mark.parametrize('echo', ['private+a/key=', 'private%2Ba%2Fkey%3D'])
def test_tool_boundary_redacts_upstream_credential_echo(echo):
    config = settings(kakao_key='private+a/key=')
    for body, status in [({'code': echo}, 401),
                         ({'documents': [{'place_name': echo}], echo: 'ignored'}, 200)]:
        with patch('requests.get', return_value=response(body, status)):
            result = invoke('search_arena', {'venue_name': '체육관'}, config)
        serialized = result.model_dump_json()
        assert echo not in serialized
        assert '[REDACTED]' in serialized


def test_kbl_service_failure_is_not_success():
    with patch('requests.get', return_value=response({'resultCode': 'Fail', 'object': None})):
        result = invoke('search_kbl_games', {'from_date': '2026-11-18', 'to_date': '2026-11-19'}, settings())
    assert not result.ok
    assert result.meta.service_code == 'Fail'


def test_kbl_candidate_id_passed_to_detail():
    row = {'gmkey': 'S49G01N75', 'gameDate': '20261118', 'gameStart': '1900',
           'tnameH': '서울 삼성', 'tnameA': '창원 LG', 'stadiumnameF': '잠실학생체육관',
           'seasonGrade': 1, 'seasonCategory': 'R'}
    with patch('requests.get', side_effect=[response([row]), response({'game': row})]) as get:
        candidates = invoke('search_kbl_games', {'from_date': '2026-11-18', 'to_date': '2026-11-18'}, settings())
        assert candidates.ok
        detail = invoke('get_kbl_game_detail', {'match_id': candidates.data[0].match_id}, settings())
    assert detail.ok and detail.data.match_id == 'S49G01N75'
    assert detail.data.start_at.isoformat() == '2026-11-18T19:00:00+09:00'
    assert get.call_args_list[1].args[0].endswith('/match/S49G01N75')
    assert get.call_args_list[0].kwargs['params']['fromDate'] == '20261118'


def test_kbl_detail_id_mismatch_is_rejected():
    with patch('requests.get', return_value=response({'game': {'gmkey': 'OTHER'}})):
        result = invoke('get_kbl_game_detail', {'match_id': 'S49G01N75'}, settings())
    assert result.error.code == 'MISSING_FIELD'


def test_kbl_empty_list_and_missing_fields():
    for body, code in [([], 'NO_RESULT'), ([{'gmkey': 'x'}], 'MISSING_FIELD')]:
        with patch('requests.get', return_value=response(body)):
            result = invoke('search_kbl_games', {'from_date': '2026-11-18', 'to_date': '2026-11-18'}, settings())
        assert result.error.code == code


def test_weather_mock_success_and_missing_target():
    target = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).replace(minute=0, second=0, microsecond=0)
    rows = [{'fcstDate': target.strftime('%Y%m%d'), 'fcstTime': target.strftime('%H%M'), 'category': k, 'fcstValue': v}
            for k, v in [('TMP', '12'), ('POP', '20'), ('PCP', '강수없음')]]
    for items, expected in [(rows, True), ([], False)]:
        body = {'response': {'header': {'resultCode': '00'}, 'body': {'items': {'item': items}, 'totalCount': len(items)}}}
        with patch('requests.get', return_value=response(body)):
            result = invoke('get_weather', {'date_time': target.isoformat(), 'lat': 37.5665, 'lon': 126.978}, settings(kma_key='a%2Bb%3D'))
        assert result.ok is expected
        if expected:
            assert result.data.precipitation_probability_pct == 20
            assert 'serviceKey' not in result.meta.actual_query


def test_weather_grid_and_base_release_boundary():
    assert grid_coordinates(37.5665, 126.9780) == (60, 127)
    kst = timezone(timedelta(hours=9))
    assert forecast_base(datetime(2026, 11, 18, 2, 9, tzinfo=kst)).strftime('%Y%m%d%H%M') == '202611172300'
    assert forecast_base(datetime(2026, 11, 18, 2, 10, tzinfo=kst)).strftime('%Y%m%d%H%M') == '202611180200'


def test_weather_rejects_naive_datetime():
    result = invoke('get_weather', {'date_time': '2026-11-18T18:00:00', 'lat': 37, 'lon': 127}, settings(kma_key='secret'))
    assert result.error.code == 'INVALID_INPUT'


def test_weather_out_of_range_without_http():
    target = datetime.now(timezone.utc) + timedelta(days=10)
    with patch('requests.get') as get:
        result = invoke('get_weather', {'date_time': target.isoformat(), 'lat': 37, 'lon': 127}, settings(kma_key='secret'))
    assert result.error.code == 'UNSUPPORTED_DATE'
    get.assert_not_called()


def test_weather_mock_service_failure():
    with patch('requests.get', return_value=response({'response': {'header': {'resultCode': '30'}}})):
        result = invoke('get_weather', {'date_time': datetime.now(timezone.utc).isoformat(), 'lat': 37, 'lon': 127}, settings(kma_key='secret'))
    assert result.error.code == 'UPSTREAM_ERROR' and result.meta.service_code == '30'


def test_result_discriminator_rejects_inconsistent_envelopes():
    with pytest.raises(ValidationError):
        ToolSuccess(ok=False, data={}, meta={'source': 'test'})
    with pytest.raises(ValidationError):
        ToolFailure(ok=True, error={'code': 'NO_RESULT', 'message': 'empty'}, meta={'source': 'test'})
