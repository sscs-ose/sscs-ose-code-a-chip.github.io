# Published numerical evidence

## Supplied measurement files received on 2026-10-30

Six CSV files from a local `Reynolds-2022-data` directory are now available
for measurement comparisons. They were supplied by the project author, who
identified them as the Zenodo data. A download URL, repository metadata and
data license were not supplied, so the Zenodo origin has not been independently
verified. The original files remain outside the checkout and are not edited or
redistributed with the application.

See [the dataset audit](reynolds2022_AUDIT.md) and
[supplied-file inventory](reynolds2022_inventory.json) for checksums,
figure/panel mapping, recorded units and measurement limitations. The CSVs contain several
independent experiments with different lengths and blank padding; a CSV row
does not represent one common observation across all its columns. Acquisition
order, header text and missing-value distinctions must be preserved. Source
labels alone are not sufficient to resolve an ambiguous unit or figure mapping.

Two mappings require particular care. In `FigS2_CircuitTesting.csv`, the header
`Current (µm)` is preserved literally; its interpretation as µA is supported by
the current axis in supplementary Fig. S2C. S2C's voltage-amplitude measurement
is a loaded circuit output, not the two-PV open-circuit voltage measured in S2E.
Also, `Fig4_PurcellBot.csv` corresponds to the main paper's **antbot** Fig. 4,
whose illumination is a 600 nm LED. The Purcell-bot and dogbot measurements use
a 660 nm laser. The filename does not justify treating those conditions as equal.

The application loader and comparison run use an explicit local source directory:

```sh
python -m examples.microrobot.reynolds_data \
  --source-dir /path/to/Reynolds-2022-data \
  --output examples/microrobot/local_runs/reynolds2022_NEW
```

Choose a fresh output directory for each run; existing nonempty results are
preserved rather than overwritten.

This is a separate measurement comparison. The digitized samples and fitted
model below remain the historical/default inputs for previously executed
circuits and layouts. Receipt of the CSVs does not retrospectively recalibrate
those experiments or establish a unique TCAD structure or actuator model.

The [direct measurement comparison](../results/reynolds2022/README.md) retains
the historical model and reports its discrepancies against the supplied samples.
A separate [training-only candidate experiment](../results/reynolds2022_fit/README.md)
tests declared voltage-bin weights and shared observation-offset hypotheses,
with specified voltage regions withheld from fitting. Its sensitivity and
withheld-region residuals do not justify promotion to the default model.
Observation offsets are hypotheses, not established instrument corrections;
neither experiment calibrates a unique physical TCAD structure.

## Historical figure digitization

`s2e_digitized.csv` is extracted from the native JPEG embedded in page 8
of the supplied 2022 supplement. It is derived from a plotted figure, not
the authors' raw samples. Source DOI, PDF hash, tick coordinates, ROI and
pixel sensitivity assumptions are in `s2e_calibration.json`.

Columns retain illumination, series-pair voltage, conventional current
entering the pair, and native x/y raster coordinates. Fig. S2E has **two
series cells**, each **540 um²**. Current is not doubled in a series pair.
The dark trace sits a few pixels above the printed zero line; it is retained
without a hidden offset correction. Adjacent raster points are correlated.

Re-fit the committed numerical evidence without downloading a paper:

```sh
python -m examples.microrobot.digitize
```

To reproduce the color extraction itself, supply the exact PDF identified
by the recorded checksum and install Poppler's `pdfimages`:

```sh
python -m examples.microrobot.digitize \
  --pdf examples/microrobot/local_references/scirobotics.abq2296_sm.pdf
```

The figure is a compressed raster. Calibration uses all five voltage
ticks and three current ticks, a fixed plot rectangle, legend exclusion,
and separate red/blue color masks. A per-column median picks each trace.
The current fit weights combine a three-pixel current floor with the
observed slope times a two-pixel voltage scale. Steep forward-current
points therefore have larger effective current uncertainty. A fixed-seed
48-trial replay perturbs global axis and per-point trace positions.
Its min/max ranges quantify these chosen digitization assumptions;
they are not experimental confidence intervals.

The ideal single-diode fit fixes series resistance to zero, shunt resistance
to infinity, and temperature to an assumed 300 K. I0 and ideality are
effective terminal parameters. The fit does not determine a unique process,
doping profile, lifetime, surface recombination or optical stack. No claim
of foundry transistor calibration follows from it.

Responsivity must state its optical-power denominator. At 1000 W/m²,
one 540 um² cell receives 540 nW; the pair receives 1080 nW. Dividing
the same string current by per-cell incident power gives twice the value
obtained using total pair incident power. Comparisons to a single-cell
TCAD result use the per-cell convention explicitly.

The paper states that its reported data are in the main text and supplement.
The Zenodo DOI returned 404 during the historical registry audit; the supplied
CSV files above now provide a separate local measurement source. The source PDF/image remains in local references;
only attributed numerical extraction and calibration metadata are included
in the application.

## Attribution and IP context

These samples are approximate digitizations of Reynolds et al. (2022),
supplement Fig. S2E, not author-provided raw data. See
[attribution and disclosed IP](../ATTRIBUTION.md) for the source, code-license
boundary and patent applications disclosed in the paper. The original PDF and
figure images are not redistributed.
