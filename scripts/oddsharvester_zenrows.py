"""Run the installed OddsHarvester through ZenRows Browser Sessions (CDP).

ZENROWS_API_KEY must be in the environment. Credentials never go into CLI
arguments or persisted endpoints. Pass OddsHarvester CLI options after --.
This adapter changes only browser transport; upstream extractors remain intact.
Reference: https://docs.zenrows.com/browser-sessions/get-started/playwright
"""
from __future__ import annotations

import os
import sys
from urllib.parse import urlencode


def complete_pinnacle_quotes(records):
    """Count explicit Pinnacle full-time triples, independently of CLI success."""
    import math
    count = 0
    for record in records:
        for quote in record.get('1x2_market') or []:
            if quote.get('bookmaker_name', '').casefold() != 'pinnacle' or quote.get('period') != 'FullTime':
                continue
            try:
                values = [float(quote[k]) for k in ('1', 'X', '2')]
            except (KeyError, ValueError, TypeError):
                continue
            if all(math.isfinite(p) and p > 1 for p in values):
                count += 1
    return count


def main():
    key = os.environ.get('ZENROWS_API_KEY')
    if not key:
        raise SystemExit('ZENROWS_API_KEY is required in the environment')
    from playwright.async_api import Browser, BrowserType, Page
    from oddsharvester.cli.cli import main as upstream_main

    parameters = {'apikey': key, 'session_ttl': '3m'}
    country = os.environ.get('ZENROWS_BROWSER_COUNTRY')
    if country:
        import re
        if not re.fullmatch('[a-z]{2}', country):
            raise SystemExit('ZENROWS_BROWSER_COUNTRY must be a lowercase two-letter code')
        parameters['proxy_country'] = country
    endpoint = 'wss://browser.zenrows.com?' + urlencode(parameters)

    async def launch_remote(self, *args, **kwargs):
        if kwargs.get('proxy'):
            raise RuntimeError('Do not combine Browser Sessions with a second launch proxy')
        try:
            return await self.connect_over_cdp(endpoint, timeout=30000)
        except Exception as exc:
            # Playwright errors include connection URLs. Do not log the raw error.
            import re
            status = re.search(r'\b(?:401|402|403|429|500|502|503)\b', str(exc))
            suffix = f' HTTP {status.group()}' if status else f' ({type(exc).__name__})'
            raise RuntimeError('ZenRows Browser Sessions connection failed' + suffix) from None

    BrowserType.launch = launch_remote
    original_context = Browser.new_context

    async def new_context(self, *args, **kwargs):
        # Optional, scoped to public target navigation through this remote
        # browser. TLS verification of the ZenRows WSS connection stays on.
        if os.environ.get('ZENROWS_IGNORE_TARGET_TLS_ERRORS') == '1':
            kwargs['ignore_https_errors'] = True
        context = await original_context(self, *args, **kwargs)
        context.set_default_navigation_timeout(30000)
        context.set_default_timeout(15000)
        return context

    Browser.new_context = new_context
    archive_dir = os.environ.get('PINNACLE_RAW_DIR')
    if archive_dir:
        import hashlib
        import json
        from datetime import datetime, timezone
        from pathlib import Path
        from urllib.parse import urlsplit
        folder = Path(archive_dir)
        folder.mkdir(parents=True, exist_ok=True)
        original_close = Page.close

        async def close_page(self, *args, **kwargs):
            if urlsplit(self.url).hostname in {'www.oddsportal.com', 'www.cuotasahora.com'}:
                try:
                    url = self.url
                    raw = (await self.content()).encode()
                    digest = hashlib.sha256(raw).hexdigest()
                    (folder / f'{digest}.html').write_bytes(raw)
                    (folder / f'{digest}.receipt.json').write_text(json.dumps({
                        'url': url, 'sha256': digest, 'bytes': len(raw),
                        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                        'transport': 'ZenRows Browser Sessions + OddsHarvester',
                        'target_tls_errors_ignored': os.environ.get('ZENROWS_IGNORE_TARGET_TLS_ERRORS') == '1',
                    }, indent=2), encoding='utf-8')
                except Exception as exc:
                    print(f'Could not archive rendered page ({type(exc).__name__})', file=sys.stderr)
            return await original_close(self, *args, **kwargs)

        Page.close = close_page
    arguments = [arg for arg in sys.argv[1:] if arg != '--']
    sys.argv = ['oddsharvester', *arguments]
    try:
        upstream_main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise
    if '--links-only' in arguments:
        return
    if '--target-bookmaker' in arguments:
        target = arguments[arguments.index('--target-bookmaker') + 1]
        if target.casefold() == 'pinnacle':
            import json
            from pathlib import Path
            option = next((o for o in ('-o', '--output') if o in arguments), None)
            if option:
                output = Path(arguments[arguments.index(option) + 1])
                if not output.suffix:
                    output = output.with_suffix('.json')
                if output.suffix == '.json' and output.exists():
                    count = complete_pinnacle_quotes(json.loads(output.read_text(encoding='utf-8')))
                    print(f'Complete Pinnacle full-time 1X2 triples: {count}')
                    if count == 0:
                        raise SystemExit(3)


if __name__ == '__main__':
    main()
