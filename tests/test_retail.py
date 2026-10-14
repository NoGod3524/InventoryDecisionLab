import csv
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from inventory_lab.core import Config, simulate
from inventory_lab.retail import load_retail, _day


class RetailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'retail.csv'
        self.config = Config(skus=1, warmup=28, days=2)
        self.headers = ['InvoiceNo', 'StockCode', 'Quantity', 'InvoiceDate', 'UnitPrice', 'Country', 'CustomerID']
        self.rows = [[str(1000+i), '10001', '2', (date(2020,1,1)+timedelta(days=i)).isoformat(), '2.35', 'United Kingdom', 'PRIVATE'] for i in range(30)]

    def write(self):
        with self.path.open('w', newline='') as f:
            w = csv.writer(f); w.writerow(self.headers); w.writerows(self.rows)

    def load(self, **kwargs):
        self.write()
        return load_retail(self.path, self.config, '2020-01-01', **kwargs)

    def test_daily_grid_decimal_and_simulator(self):
        del self.rows[2]
        replay = self.load()
        self.assertEqual(replay.demands['10001'][2], 0)
        self.assertEqual(replay.catalog[0]['unit_cost_cents'], 118)
        self.assertEqual(len(simulate(replay.config, replay.catalog, replay.demands, 'rolling_mean')), 2)
        self.assertNotIn('PRIVATE', str(replay.metadata))
        self.assertEqual(replay.metadata['currency'], 'GBP')

    def test_no_future_selection_or_price_leakage(self):
        baseline = self.load()
        self.rows += [['future', '99999', '100000', '2020-01-30', '99999', 'United Kingdom', '']]
        self.rows[-2][4] = '999999'
        changed = self.load()
        self.assertEqual(baseline.catalog, changed.catalog)
        self.assertEqual(baseline.demands, changed.demands)

    def test_adjustments_separate(self):
        self.rows += [['C1000','10001','-4','2020-01-01','2.35','United Kingdom',''],
                      ['1000','10001','-2','2020-01-01','2.35','United Kingdom',''],
                      ['1000','POST','2','2020-01-01','2.35','United Kingdom',''],
                      ['1000','10001','2','2020-01-01','0','United Kingdom','']]
        r=self.load()
        self.assertEqual(r.demands['10001'][0], 2)
        self.assertEqual(len(r.adjustments),4)
        self.assertEqual(r.adjustments[0]['reason'], 'cancellation')

    def test_duplicate_policies_and_invoice_lineage(self):
        self.rows += [self.rows[0].copy()]
        r=self.load()
        self.assertEqual(r.demands['10001'][0],4)
        self.assertEqual(r.metadata['lineage'][-1]['duplicate_of'],2)
        r=self.load(duplicate_policy='drop_exact')
        self.assertEqual(r.demands['10001'][0],2)
        with self.assertRaisesRegex(ValueError,'exact duplicate'):
            self.load(duplicate_policy='error')

    def test_distinct_invoice_rows_are_not_deduplicated(self):
        row=self.rows[0].copy(); row[2]='3'; self.rows.append(row)
        self.assertEqual(self.load(duplicate_policy='drop_exact').demands['10001'][0],5)

    def test_bad_inputs(self):
        for column, bad in [(2,'1.1'),(2,'NaN'),(4,'Infinity'),(3,'13/31/2020'),(0,'')]:
            with self.subTest(column=column,bad=bad):
                old=self.rows[0][column]; self.rows[0][column]=bad
                with self.assertRaises(ValueError): self.load()
                self.rows[0][column]=old
        self.headers[0]='Wrong'
        with self.assertRaisesRegex(ValueError,'Missing required'): self.load()

    def test_coverage_and_training_count(self):
        self.rows=self.rows[:-1]
        with self.assertRaisesRegex(ValueError,'coverage'): self.load()
        self.rows.append(['last','99999','5','2020-01-30','1','United Kingdom',''])
        self.config=replace(self.config,skus=2)
        with self.assertRaisesRegex(ValueError,'training SKUs'): self.load()

    def test_parameter_validation(self):
        for kwargs in ({'cost_ratio':'NaN'},{'cost_ratio':'0'},{'cost_ratio':'2'},{'duplicate_policy':'guess'},{'country':''}):
            with self.assertRaises(ValueError): self.load(**kwargs)
        self.config=replace(self.config,demand_scale=2)
        with self.assertRaises(ValueError): self.load()

    def test_iso_and_us_dates_are_explicit(self):
        self.assertEqual(_day('2020-01-02T10:30:01'), date(2020, 1, 2))
        self.assertEqual(_day('1/2/2020 10:30'), date(2020, 1, 2))
        self.assertEqual(_day('01/02/2020'), date(2020, 1, 2))
        with self.assertRaises(ValueError): _day('31/01/2020')
        with self.assertRaises(ValueError): _day('2020-01-02T10:30:00+01:00')

    def test_cancellation_quantity_boundaries(self):
        for qty in ('-5', '0', '5'):
            self.rows.append(['cBOUNDARY'+qty, '10001', qty, '2020-01-01', '2.35', 'United Kingdom', ''])
        r=self.load()
        self.assertEqual(r.demands['10001'][0], 2)
        self.assertEqual(r.metadata['counts']['cancellation_rows'], 3)
        self.assertEqual([a['quantity'] for a in r.adjustments], [-5, 0, 5])
        self.assertTrue(all(a['reason']=='cancellation' for a in r.adjustments))

    def test_committed_self_authored_fixture(self):
        path=Path(__file__).parent/'fixtures'/'retail.csv'
        r=load_retail(path, Config(skus=2, warmup=28, days=4), '2020-01-01')
        self.assertEqual(len(r.catalog), 2)
        self.assertEqual(r.metadata['counts']['cancellation_rows'], 2)
        self.assertEqual(r.metadata['counts']['non_product_code_rows'], 1)
        self.assertEqual(len(r.metadata['lineage']), 64)

    def test_xlsx_shared_strings(self):
        from xml.sax.saxutils import escape
        self.path=Path(self.tmp.name)/'shared.xlsx'
        ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        strings=list(dict.fromkeys(value for row in [self.headers]+self.rows for value in row))
        index={value:i for i,value in enumerate(strings)}
        xml=[]
        for n,row in enumerate([self.headers]+self.rows,1):
            cells=[f'<c r="{chr(65+c)}{n}" t="s"><v>{index[value]}</v></c>' for c,value in enumerate(row)]
            xml.append(f'<row r="{n}">'+''.join(cells)+'</row>')
        with ZipFile(self.path,'w') as z:
            z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="sales" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="/xl/worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/sharedStrings.xml',f'<sst xmlns="{ns}">'+''.join('<si><t>'+escape(value)+'</t></si>' for value in strings)+'</sst>')
            z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData>'+''.join(xml)+'</sheetData></worksheet>')
        r=load_retail(self.path,self.config,'2020-01-01')
        self.assertEqual(r.demands['10001'], [2]*30)
        self.assertEqual(r.catalog[0]['unit_cost_cents'], 118)

    def test_same_day_exact_full_match_and_privacy(self):
        self.rows += [['C1000','10001','-2','2020-01-01','2.350','United Kingdom','PRIVATE']]
        gross=self.load()
        cleaned=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(gross.demands['10001'][0], 2)
        self.assertEqual(cleaned.demands['10001'][0], 0)
        audit=cleaned.metadata['cancellation_matching']
        self.assertEqual(audit['matched_pairs'], 1)
        self.assertEqual(audit['matched_positive_units'], 2)
        self.assertEqual(audit['matched_skus'], ['10001'])
        self.assertEqual(cleaned.adjustments[0]['matched_positive_source_row'], 2)
        self.assertEqual(cleaned.adjustments[-1]['matched_cancellation_source_row'], 32)
        self.assertNotIn('PRIVATE', str(cleaned))
        self.assertNotIn('CustomerID', str(cleaned.adjustments))

    def test_same_day_exact_does_not_match_partial_other_date_or_customer(self):
        original=[r.copy() for r in self.rows]
        cases=[('-1','2020-01-01','2.35','PRIVATE'),
               ('-2','2020-02-01','2.35','PRIVATE'),
               ('-2','2020-01-01','2.36','PRIVATE'),
               ('-2','2020-01-01','2.35','OTHER'),
               ('-2','2020-01-01','2.35','')]
        for qty,day,price,customer in cases:
            self.rows=[r.copy() for r in original]
            self.rows.append(['C1000','10001',qty,day,price,'United Kingdom',customer])
            with self.subTest(qty=qty,day=day,price=price,customer=customer):
                r=self.load(cancellation_policy='same_day_exact')
                self.assertEqual(r.demands['10001'], [2]*30)
                self.assertEqual(r.metadata['cancellation_matching']['matched_pairs'],0)
        # Missing customer on both sides is deliberately insufficient evidence.
        self.rows=[r.copy() for r in original]
        self.rows[0][-1]=''
        self.rows.append(['C1000','10001','-2','2020-01-01','2.35','United Kingdom',''])
        self.assertEqual(self.load(cancellation_policy='same_day_exact').demands['10001'][0],2)

    def test_same_day_exact_different_day_inside_window_does_not_match(self):
        self.rows[0][2]='777'
        self.rows.append(['Cnextday','10001','-777','2020-01-02','2.35','United Kingdom','PRIVATE'])
        r=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(r.demands['10001'][0],777)
        self.assertEqual(r.demands['10001'][1],2)
        self.assertEqual(r.metadata['cancellation_matching']['matched_pairs'],0)

    def test_same_day_exact_duplicate_cancel_cannot_double_deduct(self):
        cancel=['C1000','10001','-2','2020-01-01','2.35','United Kingdom','PRIVATE']
        self.rows += [cancel, cancel.copy()]
        r=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(r.demands['10001'][0],0)
        self.assertEqual(r.metadata['cancellation_matching']['matched_pairs'],1)
        self.assertEqual(r.metadata['cancellation_matching']['unmatched_cancellation_rows'],1)

    def test_same_day_exact_fifo_and_no_partial_matching(self):
        self.rows += [self.rows[0].copy(), ['C1000','10001','-2','2020-01-01','2.35','United Kingdom','PRIVATE']]
        r=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(r.demands['10001'][0],2)
        self.assertEqual(r.adjustments[0]['matched_positive_source_row'],2)
        self.rows[-1][2]='-4'
        r=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(r.demands['10001'][0],4)
        self.assertEqual(r.metadata['cancellation_matching']['matched_pairs'],0)

    def test_same_day_exact_reselects_training_skus_and_costs(self):
        self.rows += [['big','99999','1000','2020-01-05','1.04','United Kingdom','PRIVATE'],
                      ['Cbig','99999','-1000','2020-01-05','1.04','United Kingdom','PRIVATE'],
                      ['expensive','10001','10','2020-01-06','100','United Kingdom','PRIVATE'],
                      ['Cexpensive','10001','-10','2020-01-06','100','United Kingdom','PRIVATE']]
        self.assertEqual(self.load().catalog[0]['sku'],'99999')
        cleaned=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(cleaned.catalog[0]['sku'],'10001')
        self.assertEqual(cleaned.catalog[0]['unit_cost_cents'],118)
        self.assertEqual(cleaned.metadata['cancellation_matching']['matched_skus'],['10001','99999'])

    def test_future_cancellation_cannot_change_training(self):
        self.rows[0][2]='100'
        baseline=self.load(cancellation_policy='same_day_exact')
        self.rows += [['Cfuture','10001','-100','2020-01-29','2.35','United Kingdom','PRIVATE']]
        after=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(baseline.catalog,after.catalog)
        self.assertEqual(baseline.demands,after.demands)
        self.assertEqual(after.metadata['cancellation_matching']['matched_pairs'],0)

    def test_cancellation_requires_negative_c_prefix_and_same_country(self):
        self.rows += [['Cpositive','10001','2','2020-01-01','2.35','United Kingdom','PRIVATE'],
                      ['negative','10001','-2','2020-01-01','2.35','United Kingdom','PRIVATE'],
                      ['Cforeign','10001','-2','2020-01-01','2.35','France','PRIVATE']]
        r=self.load(cancellation_policy='same_day_exact')
        self.assertEqual(r.demands['10001'][0],2)
        self.assertEqual(r.metadata['cancellation_matching']['matched_pairs'],0)
        with self.assertRaisesRegex(ValueError,'cancellation policy'):
            self.load(cancellation_policy='unapproved')

    def test_xlsx_inline_strings_and_numeric_dates(self):
        self.path=Path(self.tmp.name)/'retail.xlsx'
        ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        data=[self.headers]+self.rows
        xml=[]
        for n,row in enumerate(data,1):
            cells=[]
            for c,value in enumerate(row):
                ref=f'{chr(65+c)}{n}'
                if n>1 and c==3:
                    serial=(date.fromisoformat(value)-date(1899,12,30)).days
                    cells.append(f'<c r="{ref}"><v>{serial}.5</v></c>')
                else: cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>')
            xml.append(f'<row r="{n}">'+''.join(cells)+'</row>')
        with ZipFile(self.path,'w') as z:
            z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="sales" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData>'+''.join(xml)+'</sheetData></worksheet>')
        r=load_retail(self.path,self.config,'2020-01-01')
        self.assertEqual(r.demands['10001'],[2]*30)
        self.assertEqual(r.catalog[0]['unit_cost_cents'],118)


if __name__ == '__main__': unittest.main()
