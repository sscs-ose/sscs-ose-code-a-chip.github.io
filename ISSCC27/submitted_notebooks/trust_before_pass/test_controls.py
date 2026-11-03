"""Generated GUI evidence integrity; these tests are not reader evaluations."""
from pathlib import Path
import hashlib,json,re,unittest
from html.parser import HTMLParser
from build_controls import sha
from lesson import experiment,explain

P=Path(__file__).parent

class ResourceParser(HTMLParser):
    def __init__(self):super().__init__();self.remote=[];self.scripts=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script':self.scripts+=1
        for key in ['src','srcset']:
            if key in a and not a[key].startswith('data:'):self.remote.append((tag,a[key]))

class ControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d=json.loads((P/'CONTROL_DATA.json').read_text(encoding='utf-8'))

    def test_all_cached_choices_equal_current_python(self):
        self.assertEqual(len(self.d['variants']),51)
        for key,v in self.d['variants'].items():
            with self.subTest(key=key):
                for r in v['reports']:
                    fresh=experiment(r['case'],**r['settings'])
                    for field,value in r.items():self.assertEqual(value,fresh[field],(key,field))
                self.assertEqual(v['result'],v['reports'][-1])
                self.assertEqual(v['explanation'],explain(v['result']))
                self.assertIn(v['image'],self.d['images'])

    def test_source_binding_and_embedded_payload(self):
        for name,h in self.d['checker_sources'].items():self.assertEqual(sha(P/name),h)
        self.assertEqual(sha(P/'MANIFEST.json'),self.d['evidence_manifest_sha256'])
        page=(P/'INVESTIGATION_DESK.html').read_text(encoding='utf-8')
        embedded=re.search(r'<script id="experiment-data" type="application/json">(.*?)</script>',page,re.S).group(1)
        self.assertEqual(json.loads(embedded),self.d)

    def test_offline_resources_and_static_fallback(self):
        for name in ['INVESTIGATION_DESK.html','STATIC_WORKBOOK.html','START_HERE.html','TRIAL_GUIDE.html']:
            page=(P/name).read_text(encoding='utf-8');parser=ResourceParser();parser.feed(page)
            self.assertEqual(parser.remote,[])
            self.assertNotRegex(page,r'@import|url\(\s*[\"\x27]?https?://')
            if name.startswith('STATIC'):
                self.assertEqual(parser.scripts,0)
                self.assertIn('record your prediction',page)
            elif name=='INVESTIGATION_DESK.html':self.assertIn('<noscript>',page)
            else:self.assertEqual(parser.scripts,0)

    def test_reader_navigation_stays_inside_handoff(self):
        from urllib.parse import urlsplit,unquote
        files={'START_HERE.html','TRIAL_GUIDE.html','INVESTIGATION_DESK.html',
               'STATIC_WORKBOOK.html','FEEDBACK_FORM.txt','NOTICE','LICENSE'}
        for name in files:
            self.assertTrue((P/name).is_file(),name)
            if not name.endswith('.html'):continue
            page=(P/name).read_text(encoding='utf-8')
            for link in re.findall(r'href="([^"]+)"',page):
                target=unquote(urlsplit(link).path)
                if not target:continue
                self.assertIn(target,files,(name,link))
                self.assertNotIn('FACILITATOR',target)

    def test_intro_uses_existing_normal_record(self):
        page=(P/'START_HERE.html').read_text(encoding='utf-8')
        normal=self.d['variants']['rules:1.5:0.9:2']
        self.assertIn(self.d['images'][normal['image']],page)
        self.assertIn('teaching assumption',page)
        self.assertIn('oscillator-to-POR', (P/'ui/template.html').read_text(encoding='utf-8'))

    def test_key_observation_and_rule_boundaries(self):
        v=self.d['variants']
        self.assertEqual(v['window:2.5']['result']['functional']['status'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(v['window:4']['result']['functional']['status'],'FAIL')
        r=v['rules:1.5:0.9:1']['result']
        self.assertEqual((r['measurement'],r['scalar_spec'],r['functional']['status']),('VALID','FAIL','PASS'))
        self.assertNotIn('result',self.d['challenge_preview'])
        self.assertNotIn('explanation',self.d['challenge_preview'])
        self.assertEqual(v['challenge:4.4']['result']['functional']['status'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(v['challenge:6']['result']['functional']['status'],'PASS')

if __name__=='__main__':unittest.main()
