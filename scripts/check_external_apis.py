"""Run from project root. Exit 1 means at least one tool is unverified/failed."""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import KST, load_settings
from backend.tools.registry import invoke


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-date', default=datetime.now(KST).date().isoformat())
    parser.add_argument('--to-date', default=None)
    parser.add_argument('--venue', default='잠실학생체육관')
    parser.add_argument('--weather-at', default=(datetime.now(KST) + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0).isoformat())
    parser.add_argument('--lat', type=float, default=37.5665)
    parser.add_argument('--lon', type=float, default=126.9780)
    parser.add_argument('--no-env-file', action='store_true', help='Read process environment only')
    parser.add_argument('--output', type=Path, help='Optional sanitized summary JSON path')
    args = parser.parse_args()
    settings = load_settings(use_env_file=not args.no_env_file)
    calls = [
        ('search_kbl_games', {'from_date': args.from_date, 'to_date': args.to_date or args.from_date}),
        ('search_arena', {'venue_name': args.venue}),
        ('get_weather', {'date_time': args.weather_at, 'lat': args.lat, 'lon': args.lon}),
    ]
    results = {}
    for name, arguments in calls:
        result = invoke(name, arguments, settings)
        # No raw API response bodies are saved. Data is typed, allowlisted output.
        results[name] = result.model_dump(mode='json')
        if result.ok and isinstance(results[name]['data'], list):
            results[name]['sample_total_count'] = len(results[name]['data'])
            results[name]['data'] = results[name]['data'][:3]
        if name == 'search_kbl_games':
            if result.ok:
                detail = invoke('get_kbl_game_detail', {'match_id': result.data[0].match_id}, settings)
                results['get_kbl_game_detail'] = detail.model_dump(mode='json')
            else:
                results['get_kbl_game_detail'] = {'ok': False, 'skipped': True, 'reason': 'No verified candidate ID; no detail call made.'}
    report = {'mode': 'live', 'checked_at': datetime.now(KST).isoformat(),
              'note': 'Weather probe coordinates are Seoul City Hall, independent of arena candidates. Detail uses the first real candidate ID; it is skipped if candidate lookup fails.',
              'results': results}
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    # Defense in depth against an upstream echo of either credential.
    from urllib.parse import quote, unquote
    for secret in (settings.kakao_key, settings.kma_key):
        if secret:
            for variant in {secret, unquote(secret), quote(unquote(secret), safe='')}:
                serialized = serialized.replace(variant, '[REDACTED]')
    print(serialized)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + '\n', encoding='utf-8')
    return 0 if all(value['ok'] for value in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
