from decimal import Decimal
from datetime import datetime, timezone as dt_timezone
import json
import re
import time
import requests
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from pydicts import lod, casts
from moneymoney.models import Products, Quotes


class Command(BaseCommand):
    help = "Update products quotes based on ticker provider (yahoo, google, morningstar, quefondos, investingcom)"

    SUPPORTED_TICKERS = {
        'yahoo': 'ticker_yahoo',
        'google': 'ticker_google',
        'morningstar': 'ticker_morningstar',
        'quefondos': 'ticker_quefondos',
        'investingcom': 'ticker_investingcom',
        'investing_com': 'ticker_investingcom',
        'investing.com': 'ticker_investingcom',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()

    def add_arguments(self, parser):
        parser.add_argument(
            'ticker',
            type=str,
            help="Ticker provider to use (yahoo, google, morningstar, quefondos, investingcom)"
        )
        parser.add_argument(
            '--write',
            action='store_true',
            default=False,
            help="Write quotes to the database (if not provided, runs in dry-run mode)"
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help="Delay in seconds between requests to avoid rate limits (default: 1.0)"
        )

    def fetch_yahoo(self, product, ticker_value):
        """
        Fetches the latest quote for a product using Yahoo Finance API with retry and backoff on 429.
        Returns: (quote_data_dict, error_reason_str)
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        urls = [
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_value}",
            f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker_value}",
        ]

        last_status = None
        for attempt, url in enumerate(urls):
            try:
                response = self.session.get(url, headers=headers, timeout=10)
                last_status = response.status_code
                if response.status_code == 429:
                    # Rate limited: pause and try fallback URL
                    time.sleep(2.0)
                    continue
                if response.status_code != 200:
                    continue

                data = response.json()
                result = data.get('chart', {}).get('result')
                if not result:
                    return None, "No se encontraron datos de gráfico (chart)"
                meta = result[0].get('meta', {})
                price = meta.get('regularMarketPrice')
                ts = meta.get('regularMarketTime')
                if price is None:
                    return None, "No se encontró regularMarketPrice en los metadatos"
                if ts:
                    dt = datetime.fromtimestamp(ts, tz=dt_timezone.utc)
                else:
                    dt = timezone.now()
                return {
                    'datetime': dt,
                    'quote': Decimal(str(price))
                }, None
            except Exception as e:
                return None, f"Excepción / Error de conexión: {e}"

        if last_status == 429:
            return None, "HTTP 429 (Too Many Requests - Rate limit)"
        return None, f"HTTP {last_status}" if last_status else "No se pudo obtener respuesta de Yahoo"

    def fetch_google(self, product, ticker_value):
        """
        Fetches quote from Google Finance.
        Returns: (quote_data_dict, error_reason_str)
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        cookies = {'SOCS': 'CAESEwgDEgk2ODEwNjM4MTEaAmVuIAEaBgiA_LyaBg'}
        urls = [
            f"https://www.google.com/finance/quote/{ticker_value}",
        ]
        if ':' in ticker_value:
            parts = ticker_value.split(':', 1)
            urls.append(f"https://www.google.com/finance/quote/{parts[1]}:{parts[0]}")

        last_error = "No se pudo obtener la página"
        for url in urls:
            try:
                response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    continue
                # Pattern 1: data-last-price attribute
                m = re.search(r'data-last-price="([^"]+)"', response.text)
                if m:
                    price_str = m.group(1).replace(',', '')
                    return {'datetime': timezone.now(), 'quote': Decimal(price_str)}, None
                
                # Pattern 2: span jsname="Pdsbrc" or class YMlKec
                m = re.search(r'<span[^>]*jsname="Pdsbrc"[^>]*><span>([^<]+)</span>', response.text)
                if not m:
                    m = re.search(r'class="[^"]*YMlKec fxKbKc[^"]*">([^<]+)<', response.text)
                if m:
                    val_str = m.group(1).strip()
                    val_clean = re.sub(r'[^\d.,]', '', val_str)
                    if ',' in val_clean and '.' in val_clean:
                        val_clean = val_clean.replace('.', '').replace(',', '.')
                    elif ',' in val_clean:
                        val_clean = val_clean.replace(',', '.')
                    return {'datetime': timezone.now(), 'quote': Decimal(val_clean)}, None
                last_error = "No se encontró el elemento de precio en el HTML"
            except Exception as e:
                last_error = f"Excepción / Error de conexión: {e}"
        return None, last_error

    def fetch_morningstar(self, product, ticker_value):
        """
        Fetches quote from Morningstar snapshot page.
        Returns: (quote_data_dict, error_reason_str)
        """
        url = f"https://www.morningstar.es/es/funds/snapshot/snapshot.aspx?id={ticker_value}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        try:
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code not in (200, 202):
                return None, f"HTTP {response.status_code}"
            m = re.search(r'class="text">([0-9]+,[0-9]+)</td>', response.text)
            if not m:
                m = re.search(r'([0-9]+,[0-9]+)\s*EUR', response.text)
            if m:
                val_clean = m.group(1).replace(',', '.')
                return {'datetime': timezone.now(), 'quote': Decimal(val_clean)}, None
            return None, "No se encontró el valor liquidativo / precio en el HTML"
        except Exception as e:
            return None, f"Excepción / Error de conexión: {e}"

    def fetch_quefondos(self, product, ticker_value):
        """
        Fetches quote from Quefondos snapshot page.
        Returns: (quote_data_dict, error_reason_str)
        """
        urls = [
            f"https://www.quefondos.com/es/fondos/ficha/index.html?isin={ticker_value}",
            f"https://www.quefondos.com/es/fondos/ficha/index.html?ref={ticker_value}",
        ]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        last_error = "No se pudo obtener la página"
        for url in urls:
            try:
                response = self.session.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    continue
                m = re.search(r'class="floatright">([0-9]+,[0-9]+)</span>', response.text)
                if not m:
                    m = re.search(r'Valor liquidativo:[^0-9]*([0-9]+,[0-9]+)', response.text)
                if m:
                    val_clean = m.group(1).replace(',', '.')
                    return {'datetime': timezone.now(), 'quote': Decimal(val_clean)}, None
                last_error = "No se encontró el valor liquidativo en el HTML"
            except Exception as e:
                last_error = f"Excepción / Error de conexión: {e}"
        return None, last_error

    def fetch_investingcom(self, product, ticker_value):
        """
        Fetches quote for Investing.com ticker.
        Returns: (quote_data_dict, error_reason_str)
        """
        symbol = ticker_value.split('#')[0] if '#' in ticker_value else ticker_value
        url = f"https://es.investing.com/search/?q={symbol}"
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0'}
        try:
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None, f"HTTP {response.status_code}"
            m = re.search(r'class="[^"]*last-price[^"]*">([^<]+)<', response.text)
            if m:
                val_clean = m.group(1).strip().replace('.', '').replace(',', '.')
                return {'datetime': timezone.now(), 'quote': Decimal(val_clean)}, None
            return None, "No se encontró el precio en el HTML"
        except Exception as e:
            return None, f"Excepción / Error de conexión: {e}"

    def get_ticker_fetcher(self, normalized_ticker):
        fetchers = {
            'yahoo': self.fetch_yahoo,
            'google': self.fetch_google,
            'morningstar': self.fetch_morningstar,
            'quefondos': self.fetch_quefondos,
            'investingcom': self.fetch_investingcom,
        }
        return fetchers.get(normalized_ticker)

    def handle(self, *args, **options):
        raw_ticker = options['ticker'].lower().strip()
        write_mode = options['write']
        delay = options['delay']

        if raw_ticker not in self.SUPPORTED_TICKERS:
            supported = ", ".join(sorted(set(self.SUPPORTED_TICKERS.keys())))
            raise CommandError(f"Unsupported ticker provider '{raw_ticker}'. Supported: {supported}")

        ticker_field = self.SUPPORTED_TICKERS[raw_ticker]
        canonical_ticker = ticker_field.replace('ticker_', '')
        fetcher = self.get_ticker_fetcher(canonical_ticker)

        # 1. Select products: distinct products associated with investments or in favorites having that ticker
        products_qs = Products.objects.filter(
            Q(investments__isnull=False) | Q(profile__isnull=False)
        ).exclude(
            **{f"{ticker_field}__isnull": True}
        ).exclude(
            **{f"{ticker_field}": ""}
        ).select_related("stockmarkets").distinct()

        products = list(products_qs)
        selected_count = len(products)
        found_count = 0

        results = []
        not_found_results = []

        for idx, product in enumerate(products):
            ticker_val = getattr(product, ticker_field)
            if not ticker_val:
                continue

            if idx > 0 and delay > 0:
                time.sleep(delay)

            quote_data, reason = fetcher(product, ticker_val)
            if not quote_data:
                not_found_results.append({
                    "product": product.fullName(),
                    "ticker": ticker_val,
                    "reason": reason or "No se pudo obtener la cotización",
                })
                continue

            found_count += 1
            dt = quote_data['datetime']
            quote_val = quote_data['quote']

            # Determine whether this quote would be an insert or update
            is_update = Quotes.objects.filter(products=product, datetime=dt).exists()
            action = "update" if is_update else "insert"

            results.append({
                "product": product.fullName(),
                "datetime": dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                "quote": quote_val,
                "action": action,
            })

            if write_mode:
                quote_obj = Quotes(products=product, datetime=dt, quote=quote_val)
                quote_obj.save()

        if results:
            lod.lod_print(results)
        else:
            self.stdout.write("No se encontraron cotizaciones.")

        if not_found_results:
            self.stdout.write("\nNo encontrados:")
            lod.lod_print(not_found_results)

        self.stdout.write(f"\nSeleccionados: {selected_count}")
        self.stdout.write(f"Buscados: {found_count}")
