# Reynolds 2022 supplied CSV audit

Audited 2026-10-30, read-only, from `<USER_HOME>/Downloads/Reynolds-2022-data`.
The six files contain 12,950,695 bytes and 1,400,415 numeric cells. No source
files or existing project files were changed. No raw CSV series are reproduced
here. [The inventory](reynolds2022_inventory.json) records SHA256, size, exact
headers, per-column counts, bounds, original-order statistics and section maps.

The user reports a Zenodo origin. These local files have **not** been matched to
an independently retrieved archive or published archive checksums; authorship,
version and the data license remain unverified. The article DOI is
`10.1126/scirobotics.abq2296`; its printed data DOI is
`10.5281/zenodo.7008281`. This audit does not resolve the earlier registry failure
recorded in [references.md](../references.md), and does not authorize data
redistribution. Local hashes establish reproducible file identity only.

## Schema and completeness

Columns below are one-based; counts exclude the header. Panel identifications
combine filenames/headers with the locally held article and supplement captions,
so they are interpretations rather than embedded CSV metadata.

| File | Data rows × columns | Independent groups: columns, complete observations | Numeric / blank cells |
|---|---:|---|---:|
| `Fig3_PurcellBot.csv` | 230 × 4 | 1–2 Purcell displacement: 230; 3–4 inset: 9 | 478 / 442 |
| `Fig4_PurcellBot.csv` | 745 × 6 | 1–3 **antbot** displacement/speed: 745; 4–6 feet: 60 | 2,415 / 2,055 |
| `Fig5_Dogbot.csv` | 201 × 2 | 1–2 dogbot position: 201 | 402 / 0 |
| `FigS2_CircuitTesting.csv` | 100,004 × 17 | 1–2 current at 2.5 sun: 100,004; 3–4 at 7 sun: 100,004; 5–7 phase voltages: 100,004; 8–9 voltage/light: 22; 10–11 current/light: 27; 12–13 frequency/light: 32; 14–15 dark PV IV: 15,003; 16–17 one-sun PV IV: 15,003 | 760,202 / 939,866 |
| `FigS4_LEGO_purcell.csv` | 6 × 4 | 1–2 LEGO displacement: 6; 3–4 inset: 5 | 22 / 2 |
| `FigS6_DogbotCircuit.csv` | 318,448 × 2 | **1 current (nA), 2 time (s)**: 318,448 | 636,896 / 0 |

All six have one header row and uniform row widths. Every nonblank data cell
parses as a finite number: zero invalid tokens, NaN/inf values or internal blank
holes. Within every independent group all columns end together, with zero
partially filled observations. All blank cells are trailing section padding;
do not drop a row merely because an unrelated section is blank or join different
sections by CSV row number. Every explicitly labeled time column is strictly
increasing. `Fig4` and `FigS2` require the documented cp1252 fallback after strict
UTF-8 decoding fails; the other files decode with UTF-8-sig.

The literal S2 column 11 header is `Current (µm)`. It is dimensionally wrong.
The coordinator visually checked Fig. S2C's right axis, which explicitly gives
current in µA; interpret this column as µA while retaining the literal header.
The evidence is the local supplement PDF, SHA256
`43138926560d636d64845f7f708ba6026e26446f79df2962cc8e1355ed6b9fd4`, page 8.
No numerical unit conversion or source edit was applied in this inventory.

## Electrical domains and interpretation

- **S2A:** two current waveforms, 0–5.00015 s, nominal 50 µs sampling. Headers
  say 2.5 and 7 sun and µA. The supplement specifies 660 nm light and the lowest
  frequency selection. Ranges are −0.336307 to +0.373647 µA and −1.38263 to
  +1.38263 µA. These bipolar circuit-output waveforms are not PV IV curves.
- **S2B:** shared time 0–10.0003 s, nominal 100 µs sampling; phase 1 spans
  −0.597810 to +0.571450 V, phase 2 −0.622970 to +0.667446 V. The paper
  describes two simultaneous phase outputs separated by about 90 degrees. Its
  voltage method uses a 100 MΩ load and an Ithaco 1211 preamplifier with current
  conversion: this is a loaded output measurement, not unique PV open circuit.
- **S2C:** independent measured square-wave voltage/current amplitudes versus
  incident irradiance, 0.0282942–7.01696 kW/m². Voltage spans
  0.118368–0.665820 V, interpreted current 0.001900–1.285000 µA. Approximately
  0.6 V is a circuit output amplitude, not the two-cell PV pair Voc. Repeated
  irradiance entries and ordering resets exist; no replicate IDs explain them.
- **S2D:** 32 frequency observations over that same irradiance range, spanning
  0.227946–12.0934 Hz. The supplement says this circuit was wired to a nominal
  8 Hz output setting. It does not establish a universal light/frequency law for
  other divider settings, device temperatures, spectra or geometries.
- **S2E:** the actual PV terminal IV data are columns 14–17. Each dark/light
  curve has 15,003 observations, about 1,060 unique voltages, repeated values,
  numerous direction changes and no time or sweep-direction column. Dark spans
  −1.29002 to +1.32695 V; one sun spans −1.29749 to +1.32695 V. Do not assume a
  monotonic or single-valued sweep, silently sort/deduplicate, or identify branch
  differences as hysteresis without acquisition metadata. The supplement
  identifies two **large actuator PVs in series**, each area 540 µm², at
  1 kW/m² for the illuminated curve; these are not the logic PV pair.
- **S6C:** current-first schema, 0–6.36894 s, nominal 20 µs sampling,
  −304.682 to +286.981 nA. The paper describes on-chip optical shift commands
  that double output frequency. The CSV contains no command timestamps,
  illumination trace, bitstream, voltage or receiver-decode state; timing markers
  in the figure are not additional measured columns.

The CSV headers contain no temperatures, uncertainties, instrument settings,
replicate/device identifiers or explicit normalization/correction metadata.
Wavelength/measurement-method/area statements above come from local paper
context, not headers. No CSV confirms a 300 K measurement temperature, individual
PV geometry beyond the caption area, doping, thickness, Rs/Rsh, logic-PV scaling,
or transient storage capacitance. Such parameters cannot be uniquely calibrated
from these terminal observations.

## Conditional comparison with the existing digitized PV pair

No fit, parameter update, filtering or dark-offset subtraction was performed.
This is a direct descriptive comparison with
`results/published/pv_fit.json`, which fits raster-digitized S2E and assumes 300 K.
The illuminated current is negative in the generating quadrant; delivered
current/power therefore use −I and −VI. This sign interpretation matches the
figure and the existing raster convention, rather than an explicit CSV sign note.

For |V| < 0.01 V, the supplied one-sun series has 130 samples: median delivered
current **148.106 nA**, range 147.374–149.083 nA. The old model's photocurrent is
145.262369 nA; the observed median is about 1.96% above that value. This narrow voltage-window median is not an
exact zero-voltage interpolation or a new fitted Isc. The analogous 127 dark
samples have positive terminal-current median **1.86163 nA** (1.40385–2.41096 nA),
and **the full dark series never crosses zero**. Preserve that measured offset;
subtracting it would be an additional correction requiring a stated rationale.

Four adjacent illuminated zero-current sign changes yield linear-interpolated
crossings from **1.2349670 to 1.2479000 V**. The old model's Voc 1.2452557 V lies
within this observed range; the range is not a confidence interval. The largest
individual supplied generating-power sample is **161.782472 nW at 1.12934 V**
(143.254 nA delivered), versus the old smooth model's maximum 147.385971 nW at
1.0707048 V. The roughly 9.77% difference compares a noisy sampled maximum with
a fitted-model maximum and is method dependent. These checks support the same
approximate pair scale; they neither validate the old curve over its full domain
nor establish calibrated device physics or a new accuracy tolerance.

## Mechanics domains and corrections

- **Fig. 3B, Purcell-bot:** center-tracked displacement, 0–22.9 s in 0.1 s
  steps, 0–113.970 µm; inset 0–0.8 s, 0–9.4366 µm. Endpoint displacement/time
  is 4.964585 µm/s. Paper context gives a smooth silicon wafer, about 1 Hz gait,
  illumination below 1 kW/m², 660 nm laser power and separate halogen imaging.
- **Fig. 4B/C/E, antbot:** the filename's `PurcellBot` label conflicts with the
  paper's explicit antbot caption. Displacement covers 0–37.2 s in 0.05 s
  steps, 0–428.492 µm, endpoint average 11.518602 µm/s; supplied speed spans
  −56.6056 to +93.8982 µm/s. Foot observations cover 0–2.95 s in 0.05 s steps,
  explicitly in µm, and are body-relative in the paper. The paper gives a glass
  coverslip, about 2.5 Hz gait, about 4 kW/m² and a 600 nm LED. Supplied speed
  agrees with `numpy.gradient(distance,time)` to RMS 0.00346033 µm/s, maximum
  0.00970001 µm/s after printed-value rounding, consistent with a finite
  difference derivative; its independence as a second measurement is unproven.
- **Fig. 5D, dogbot:** position 0–10 s in 0.05 s steps, 0–39.6229 µm;
  endpoint average 3.837440 µm/s. The caption places a shift command at 5 s and
  says gait frequency doubles. The paper specifies 660 nm laser power and
  halogen imaging; the CSV has no irradiance or command measurement channel.
- **S4C:** **macroscale LEGO** Purcell model, main 0–24 s at 4.8 s intervals,
  0–50.3389 **cm**; inset 0–4.8 s at 1.2 s intervals, 0–10.9313 cm. This is a
  qualitative gait comparison, not a microscopic actuator calibration.

Each displacement/position group begins at zero, so these are origin-referenced
figure series rather than unreduced video coordinates. No headers document drift
correction, geometric normalization, frame averaging or tracking uncertainty;
zero origins do not prove any particular correction procedure. Negative speeds
and backward displacement steps are retained. The curves alone cannot identify
leg friction, force, contact state, hydrodynamic drag or electrochemical hinge
parameters; published body-size estimates must not be substituted for missing
actuator geometry. Endpoint averages above are aggregate descriptors, not fitted
steady velocities.

## Executed checks and reproduction

Executed local Python stdlib CSV/encoding/hash scans for all six files; numerical
exploration used the existing `.venv` NumPy for IV window, sign-change, sampled
power and speed-derivative summaries. No simulator, network provenance check,
parameter fitting or new dependency installation was run. Strict UTF-8 first
failed on Fig. 4, prompting the documented cp1252 fallback; an inefficient initial
missingness scan was interrupted and replaced with a completed linear scan.

The inventory generator below is self-contained stdlib Python. Run it from the
repository root using `.venv/bin/python` (adjust `SOURCE` for another local copy).
It rewrites **only** this inventory. Unit-override visual evidence is credited to
the coordinator; the generator does not re-perform that visual check. The audit
summaries describe these supplied files; acceptance remains with the coordinator.
Archive provenance, license and physical parameter calibration remain unresolved.

```python
import csv, hashlib, json, math
from collections import Counter
from pathlib import Path

SOURCE = Path('<USER_HOME>/Downloads/Reynolds-2022-data')
OUTPUT = Path('examples/microrobot/data/reynolds2022_inventory.json')
GROUPS = {
 'Fig3_PurcellBot.csv': [('purcell_displacement', [1,2], 'Fig. 3B'), ('purcell_inset', [3,4], 'Fig. 3B inset')],
 'Fig4_PurcellBot.csv': [('antbot_displacement_speed', [1,2,3], 'Fig. 4B/C'), ('antbot_feet', [4,5,6], 'Fig. 4E')],
 'Fig5_Dogbot.csv': [('dogbot_displacement', [1,2], 'Fig. 5D')],
 'FigS2_CircuitTesting.csv': [('output_current_2p5_sun', [1,2], 'Fig. S2A'), ('output_current_7_sun', [3,4], 'Fig. S2A'), ('phase_voltages', [5,6,7], 'Fig. S2B'), ('voltage_vs_irradiance', [8,9], 'Fig. S2C'), ('current_vs_irradiance', [10,11], 'Fig. S2C'), ('frequency_vs_irradiance', [12,13], 'Fig. S2D'), ('pv_dark_iv', [14,15], 'Fig. S2E'), ('pv_1_sun_iv', [16,17], 'Fig. S2E')],
 'FigS4_LEGO_purcell.csv': [('lego_displacement', [1,2], 'Fig. S4C'), ('lego_inset', [3,4], 'Fig. S4C inset')],
 'FigS6_DogbotCircuit.csv': [('dogbot_output_current', [1,2], 'Fig. S6C')],
}
files=[]
for path in sorted(SOURCE.glob('*.csv')):
 raw=path.read_bytes()
 try:
  decoded=raw.decode('utf-8-sig'); encoding='utf-8-sig'
 except UnicodeDecodeError:
  decoded=raw.decode('cp1252'); encoding='cp1252'
 rows=list(csv.reader(decoded.splitlines())); header=rows[0]; data=rows[1:]
 columns=[]
 for col, label in enumerate(header):
  values=[]; numeric_rows=[]; blanks=[]; invalid=[]; nonfinite=[]
  for rownum,row in enumerate(data,2):
   cell=row[col].strip() if col<len(row) else ''
   if not cell:
    blanks.append(rownum);continue
   try: value=float(cell)
   except ValueError:
    invalid.append(rownum);continue
   numeric_rows.append(rownum)
   if math.isfinite(value): values.append(value)
   else: nonfinite.append(rownum)
  first=min(numeric_rows) if numeric_rows else None
  last=max(numeric_rows) if numeric_rows else None
  internal=[r for r in blanks if first is not None and first<=r<=last]
  delta=[b-a for a,b in zip(values,values[1:])]
  units=label.rsplit('(',1)[-1].rstrip(')') if '(' in label else None
  summary={'index_1based':col+1, 'header_literal':label, 'unit_literal':units,
   'numeric_count':len(numeric_rows), 'finite_count':len(values), 'blank_count':len(blanks),
   'invalid_rows_1based':invalid, 'nonfinite_rows_1based':nonfinite,
   'first_numeric_row_1based':first, 'last_numeric_row_1based':last,
   'internal_blank_rows_1based':internal,
   'trailing_blank_count':sum(r>last for r in blanks) if last is not None else len(blanks),
   'minimum':min(values) if values else None, 'maximum':max(values) if values else None,
   'first_value':values[0] if values else None, 'last_value':values[-1] if values else None,
   'unique_numeric_values':len(set(values)), 'zero_count':sum(v==0 for v in values),
   'adjacent_increasing_count':sum(d>0 for d in delta), 'adjacent_equal_count':sum(d==0 for d in delta),
   'adjacent_decreasing_count':sum(d<0 for d in delta)}
  if path.name=='FigS2_CircuitTesting.csv' and col==10:
   summary.update({'unit_interpreted':'µA','unit_override_basis':'Literal CSV unit µm is dimensionally inconsistent with current; Fig. S2C right axis explicitly labels Current (µA), visually verified by coordinator from local supplement PDF SHA256 43138926560d636d64845f7f708ba6026e26446f79df2962cc8e1355ed6b9fd4. No CSV value changed.'})
  columns.append(summary)
 groups=[]
 for name, indexes, panel in GROUPS[path.name]:
  complete=[n for n,row in enumerate(data,2) if all(i<=len(row) and row[i-1].strip() for i in indexes)]
  patterns=Counter(tuple(bool(i<=len(row) and row[i-1].strip()) for i in indexes) for row in data)
  groups.append({'name':name,'columns_1based':indexes,'paper_panel_interpretation':panel,
   'panel_mapping_basis':'Filename, literal headers, and local main-paper/supplement figure captions; not embedded CSV panel metadata.',
   'complete_numeric_row_count':len(complete),'first_complete_row_1based':min(complete), 'last_complete_row_1based':max(complete),
   'partial_row_count':sum(n for pat,n in patterns.items() if any(pat) and not all(pat)),
   'all_blank_row_count':sum(n for pat,n in patterns.items() if not any(pat))})
 files.append({'filename':path.name,'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
  'decoding_used':encoding,'utf8_bom_present':raw.startswith(b'\xef\xbb\xbf'),
  'csv_rows_including_header':len(rows),'data_rows':len(data),'column_count':len(header),
  'row_width_counts':{str(k):v for k,v in sorted(Counter(map(len,rows)).items())},
  'numeric_cell_count':sum(c['numeric_count'] for c in columns), 'blank_cell_count':sum(c['blank_count'] for c in columns),
  'non_numeric_nonblank_cell_count':sum(len(c['invalid_rows_1based']) for c in columns),
  'columns':columns,'independent_groups':groups})
result={'schema_version':1,'audit_date':'2026-10-30','source_directory':str(SOURCE),
 'source_handling':'Read-only local audit; no input values or input files modified; this inventory includes aggregate statistics and headers, not copied data rows.',
 'provenance':{'user_reported_origin':'Zenodo / Reynolds 2022 data','independently_authenticated':False,
  'article_doi':'10.1126/scirobotics.abq2296','article_printed_data_doi':'10.5281/zenodo.7008281',
  'license_independently_confirmed':False,'archive_matching_checksums_available':False,
  'limitation':'Local hashes identify the supplied files, not their authorship, license or correspondence to an independently retrieved archive.'},
 'numeric_conventions':{'csv_row_numbers':'1-based, header is row 1','column_numbers':'1-based',
  'blank':'Empty or whitespace-only CSV cell; trailing padding counted separately from internal gaps.',
  'unit_policy':'Preserve literal headers; only separately document the evidence-backed S2C current unit interpretation.',
  'statistics':'Computed on parsed finite values in original row order, without sorting, deduplicating, offset subtraction, normalization, resampling or fitting.',
  'groups':'Independent side-by-side tables; do not join unrelated groups using the shared CSV row number.'},
 'total_size_bytes':sum(f['size_bytes'] for f in files),'total_numeric_cells':sum(f['numeric_cell_count'] for f in files),
 'files':files}
OUTPUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'files':len(files),'bytes':result['total_size_bytes'],'numeric_cells':result['total_numeric_cells'],
 'file_summaries':[{k:f[k] for k in ('filename','size_bytes','sha256','data_rows','numeric_cell_count','blank_cell_count')} for f in files]},indent=2))
```
