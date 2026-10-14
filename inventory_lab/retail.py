"""UCI sales replay adapter. No customer identifiers leave the input reader."""
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import csv
import hashlib
import json
from pathlib import Path
import posixpath
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from .core import Config, validate_data

SOURCE_URL = 'https://archive.ics.uci.edu/dataset/352/online+retail'
SOURCE_DOI = 'https://doi.org/10.24432/C5BW33'
REQUIRED = ('InvoiceNo', 'StockCode', 'Quantity', 'InvoiceDate', 'UnitPrice', 'Country')
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


@dataclass
class RetailReplay:
    config: Config
    catalog: list
    demands: dict
    metadata: dict
    adjustments: list


def _headers(values):
    values = [str(v).strip() for v in values]
    if len(values) != len(set(values)) or any(not v for v in values):
        raise ValueError('Column names must be unique and nonempty')
    missing = set(REQUIRED) - set(values)
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(sorted(missing)))
    return values


def _xlsx_rows(path):
    """Read the first sheet, shared/inline strings, and raw numeric date serials."""
    with ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 1_500_000_000:
            raise ValueError('XLSX uncompressed size exceeds safety limit')
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        props = workbook.find(NS + 'workbookPr')
        if props is not None and props.get('date1904') in ('1', 'true'):
            raise ValueError('1904 date-system workbooks are unsupported; export ISO-date CSV')
        sheet = workbook.find(NS + 'sheets/' + NS + 'sheet')
        if sheet is None:
            raise ValueError('Workbook has no worksheet')
        rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = [r.get('Target') for r in rels if r.get('Id') == rid and r.get('TargetMode') != 'External']
        if len(targets) != 1:
            raise ValueError('Invalid first worksheet relationship')
        target = targets[0]
        sheet_path = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            with archive.open('xl/sharedStrings.xml') as stream:
                for _, node in ET.iterparse(stream, events=('end',)):
                    if node.tag == NS + 'si':
                        shared.append(''.join(n.text or '' for n in node.iter(NS + 't')))
                        node.clear()
        headers = None
        with archive.open(sheet_path) as stream:
            for _, node in ET.iterparse(stream, events=('end',)):
                if node.tag != NS + 'row':
                    continue
                values = {}
                for cell in node.findall(NS + 'c'):
                    if cell.find(NS + 'f') is not None:
                        raise ValueError('Formula cells are unsupported; export values-only CSV')
                    ref = cell.get('r', '')
                    match = re.fullmatch(r'([A-Z]+)[0-9]+', ref)
                    if not match:
                        raise ValueError('Missing/invalid spreadsheet cell reference')
                    column = 0
                    for char in match[1]:
                        column = column * 26 + ord(char) - 64
                    value = cell.findtext(NS + 'v', '')
                    if cell.get('t') == 's':
                        value = shared[int(value)]
                    elif cell.get('t') == 'inlineStr':
                        value = ''.join(n.text or '' for n in cell.iter(NS + 't'))
                    elif cell.get('t') in ('e', 'b'):
                        raise ValueError('Error/boolean cells are unsupported')
                    values[column - 1] = value
                line = int(node.get('r', '0'))
                node.clear()
                if not values or not any(str(v).strip() for v in values.values()):
                    continue
                if headers is None:
                    headers = _headers([values.get(i, '') for i in range(max(values) + 1)])
                    continue
                if max(values) >= len(headers):
                    raise ValueError(f'Row {line}: too many columns')
                yield line, {h: str(values.get(i, '')).strip() for i, h in enumerate(headers)}
        if headers is None:
            raise ValueError('Empty workbook')


def _rows(path):
    if path.suffix.lower() == '.xlsx':
        yield from _xlsx_rows(path)
    elif path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream)
            try:
                headers = _headers(next(reader))
            except StopIteration:
                raise ValueError('Empty CSV') from None
            for values in reader:
                if not values:
                    continue
                if len(values) != len(headers):
                    raise ValueError(f'Row {reader.line_num}: incorrect number of columns')
                yield reader.line_num, dict(zip(headers, (v.strip() for v in values)))
    else:
        raise ValueError('Use a .csv or .xlsx input file (extract UCI ZIP first)')


def _number(value, field):
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(f'Invalid {field}: {value!r}') from None
    if not result.is_finite():
        raise ValueError(f'{field} must be finite')
    return result


def _day(value, excel=False):
    if excel and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
        serial = _number(value, 'InvoiceDate')
        if not 61 <= serial <= 2958465:
            raise ValueError('Invalid Excel date serial')
        return date(1899, 12, 30) + timedelta(days=int(serial))
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is not None:
            raise ValueError('Use local naive invoice timestamps')
        return result.date()
    except ValueError:
        pass
    # UCI CSV exports convention: month/day/year. Never guess day/month.
    for fmt in ('%m/%d/%Y %H:%M', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError('InvoiceDate must be ISO, US month/day/year, or an XLSX serial')


def load_retail(path, config, start_date, country='United Kingdom',
                duplicate_policy='keep', cost_ratio='0.5', cancellation_policy='gross'):
    """Replay gross positive recorded sales. SKU ranking/costs use training only.

    ``config`` uses pence for every *_cents field in this GBP replay. Acquisition
    cost is an assumed fraction of training quantity-weighted selling price.
    Duplicate policy is explicit: keep, drop_exact, or error.
    same_day_exact cancels whole matching rows with nonempty identical CustomerID;
    it is an audit-driven, post-hoc quality sensitivity, not preregistered cleaning.
    """
    config.validate()
    if config.demand_scale != 1:
        raise ValueError('Real sales replay requires demand_scale=1')
    if cancellation_policy not in ('gross', 'same_day_exact'):
        raise ValueError('Unknown cancellation policy')
    if duplicate_policy not in ('keep', 'drop_exact', 'error'):
        raise ValueError('Unknown duplicate policy')
    if not isinstance(country, str) or not country.strip():
        raise ValueError('Specify a nonempty country')
    ratio = _number(str(cost_ratio), 'cost_ratio')
    if not 0 < ratio <= 1:
        raise ValueError('cost_ratio must be in (0, 1]')
    start = date.fromisoformat(start_date) if isinstance(start_date, str) else start_date
    if type(start) is not date:
        raise ValueError('start_date must be a date or ISO date string')
    split = start + timedelta(days=config.warmup)
    end = split + timedelta(days=config.days - 1)
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    seen, counts, adjustments = {}, Counter(), []
    units, revenue = Counter(), defaultdict(Decimal)
    daily, lineage = defaultdict(Counter), defaultdict(list)
    sales, cancellation_candidates = [], []
    matchable_sales = defaultdict(deque)
    negative_cancellations = 0
    first = last = None
    for line, row in _rows(path):
        counts['source_rows'] += 1
        try:
            invoice, sku = row['InvoiceNo'], row['StockCode']
            if not invoice or not sku or not row['Country']:
                raise ValueError('InvoiceNo, StockCode and Country cannot be blank')
            quantity = _number(row['Quantity'], 'Quantity')
            if quantity != quantity.to_integral_value():
                raise ValueError('Quantity must be an integer')
            qty = int(quantity)
            price = _number(row['UnitPrice'], 'UnitPrice')
            day = _day(row['InvoiceDate'], path.suffix.lower() == '.xlsx')
        except (ValueError, OverflowError) as exc:
            raise ValueError(f'Row {line}: {exc}') from exc
        # Hash full original row, including CustomerID, but never export it.
        key = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).digest()
        duplicate_of = seen.get(key)
        if duplicate_of is not None:
            counts['exact_duplicate_rows'] += 1
            if duplicate_policy == 'error':
                raise ValueError(f'Row {line}: exact duplicate of row {duplicate_of}')
            if duplicate_policy == 'drop_exact':
                counts['dropped_duplicate_rows'] += 1
                continue
        else:
            seen[key] = line
        if row['Country'] != country:
            counts['other_country_rows'] += 1
            continue
        first = day if first is None else min(first, day)
        last = day if last is None else max(last, day)
        if not start <= day <= end:
            counts['outside_window_rows'] += 1
            continue
        entry = dict(source_row=line, invoice=invoice, sku=sku, date=day.isoformat(),
                     quantity=qty, unit_price_gbp=str(price), duplicate_of=duplicate_of)
        if invoice.upper().startswith('C') or qty < 0:
            entry['reason'] = 'cancellation' if invoice.upper().startswith('C') else 'return_or_negative_quantity'
            adjustments.append(entry)
            counts[entry['reason'] + '_rows'] += 1
            if invoice.upper().startswith('C') and qty < 0:
                negative_cancellations += 1
                customer = row.get('CustomerID', '')
                if cancellation_policy == 'same_day_exact' and customer:
                    match_key = (day, sku, price, -qty, country, customer)
                    cancellation_candidates.append((match_key, entry))
        elif qty == 0 or price <= 0 or not re.fullmatch(r'\d{5}[A-Za-z]*', sku):
            entry['reason'] = 'zero_quantity' if qty == 0 else ('nonpositive_price' if price <= 0 else 'non_product_code')
            adjustments.append(entry)
            counts[entry['reason'] + '_rows'] += 1
        else:
            counts['eligible_sales_rows'] += 1
            sales.append((entry, day, price))
            customer = row.get('CustomerID', '')
            if cancellation_policy == 'same_day_exact' and customer:
                matchable_sales[(day, sku, price, qty, country, customer)].append(entry)
    # Match only within calendar day, before constructing training/evaluation data.
    # Separate source-order queues make one-to-one FIFO deterministic even if the
    # workbook is unsorted. Customer IDs stay in temporary keys, never output.
    matched_rows, matched_skus, matched_units = set(), set(), 0
    for match_key, cancellation in cancellation_candidates:
        candidates = matchable_sales.get(match_key)
        if not candidates:
            continue
        positive = candidates.popleft()
        matched_rows.add(positive['source_row'])
        matched_skus.add(positive['sku'])
        matched_units += positive['quantity']
        cancellation['matched_positive_source_row'] = positive['source_row']
        cancellation['matched_positive_invoice'] = positive['invoice']
        adjustments.append(dict(positive,
            reason='same_day_exact_matched_positive',
            matched_cancellation_source_row=cancellation['source_row'],
            matched_cancellation_invoice=cancellation['invoice']))
    # Drop temporary customer-linked keys as soon as the audit pairing is finished.
    matchable_sales.clear()
    cancellation_candidates.clear()
    for entry, day, price in sales:
        if entry['source_row'] in matched_rows:
            continue
        sku, qty = entry['sku'], entry['quantity']
        daily[sku][(day - start).days] += qty
        lineage[sku].append(entry)
        if day < split:
            units[sku] += qty
            revenue[sku] += price * qty
    counts['retained_sales_rows'] = len(sales) - len(matched_rows)
    counts['matched_positive_rows'] = len(matched_rows)
    if first is None or first > start or last < end:
        raise ValueError('Requested window exceeds observed country date coverage')
    ranked = sorted(units, key=lambda sku: (-units[sku], sku))
    if len(ranked) < config.skus:
        raise ValueError(f'Only {len(ranked)} eligible training SKUs; requested {config.skus}')
    selected = ranked[:config.skus]
    catalog = [dict(sku=sku, unit_cost_cents=max(1, int((revenue[sku] / units[sku] * ratio * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))), lead_days=config.lead_days) for sku in selected]
    demands = {sku: [daily[sku][i] for i in range(config.warmup + config.days)] for sku in selected}
    validate_data(config, catalog, demands)
    metadata = dict(mode='historical_sales_replay', source_url=SOURCE_URL, source_doi=SOURCE_DOI,
        source_citation='Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository.',
        source_license='CC BY 4.0', source_sha256=digest.hexdigest(), source_filename=path.name,
        currency='GBP', money_minor_unit='pence (legacy field names end in _cents)',
        country=country, start_date=start.isoformat(), training_end=(split-timedelta(days=1)).isoformat(),
        evaluation_start=split.isoformat(), end_date=end.isoformat(), duplicate_policy=duplicate_policy,
        cancellation_policy=cancellation_policy,
        cancellation_matching=dict(matched_pairs=len(matched_rows), matched_positive_units=matched_units,
            matched_skus=sorted(matched_skus),
            unmatched_cancellation_rows=negative_cancellations-len(matched_rows),
            negative_cancellation_rows=negative_cancellations,
            rule='Whole-row same calendar day/SKU/Decimal price/absolute quantity/country/nonempty exact CustomerID; one-to-one source-row FIFO',
            interpretation='Post-hoc audit-driven data-quality sensitivity; not preregistered; pairing does not prove original invoice correspondence'),
        counts=dict(sorted(counts.items())), selected_skus=selected,
        selection='Top retained positive units in training only after chosen cancellation policy; lexical SKU tie-break',
        acquisition_cost_assumption='Training quantity-weighted selling price times cost_ratio; half-up pence; minimum 1p',
        cost_ratio=str(ratio), zero_fill='All absent SKU/calendar-day sales become zero; closure vs missing vs stockout unknown',
        demand_caveat='Recorded sales are not latent demand. Replenishment, cost and lost-sales outcomes are hypothetical.',
        lineage=[entry for sku in selected for entry in lineage[sku]])
    return RetailReplay(config, catalog, demands, metadata, adjustments)
