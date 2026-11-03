import re

def parse_FD_tecplot(filename):
    with open(filename, "r") as f:
        lines = f.readlines()

    variables = []
    datasets = []

    current_params = {}
    current_data = []

    reading_variables = False
    reading_data = False

    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # --------------------------------------------------------
        # VARIABLES
        # --------------------------------------------------------

        if line.startswith("VARIABLES"):
            reading_variables = True

            vars_found = re.findall(r'"([^"]+)"', line)
            variables.extend([v.strip() for v in vars_found])

            i += 1

            while i < len(lines):
                l = lines[i].strip()

                if l.startswith('"'):
                    variables.append(l.strip('" ').strip())
                    i += 1
                else:
                    break

            reading_variables = False
            continue

        # --------------------------------------------------------
        # NEW ZONE
        # --------------------------------------------------------
        if line.startswith("ZONE"):
            if current_data:
                datasets.append({
                    "params": current_params.copy(),
                    "data": current_data
                })

            current_data = []
            current_params = {}

            # Data starts immediately after ZONE unless AUXDATA follows.
            reading_data = True

            i += 1
            continue

        # --------------------------------------------------------
        # AUXDATA / DATASETAUXDATA
        # --------------------------------------------------------
        if line.startswith(("AUXDATA", "DATASETAUXDATA")):

            matches = re.findall(
                r'(?:AUXDATA|DATASETAUXDATA)\s+(\S+)\s*=\s*"\s*([^"]+)"',
                line
            )

            for name, value in matches:
                try:
                    current_params[name] = float(value)
                except ValueError:
                    # Ignore non-numeric metadata such as TIME
                    pass

            i += 1
            continue

        # --------------------------------------------------------
        # Numerical data
        # --------------------------------------------------------
        if reading_data:
            if (line.startswith("ZONE")
                    or line.startswith("End of Xyce")
                    or line == ""):
                reading_data = False
                continue

            try:
                values = [float(v) for v in line.split()]
                current_data.append(values)

            except ValueError:
                pass

        i += 1

    # append final zone

    if current_data:
        datasets.append({
            "params": current_params.copy(),
            "data": current_data
        })

    return variables, datasets

def parse_TD_tecplot(filename):

    with open(filename, "r") as f:
        lines = f.readlines()

    variables = []
    datasets = []

    current_params = {}
    current_data = []

    reading_data = False

    i = 0

    while i < len(lines):

        line = lines[i].strip()

        # --------------------------------------------------------
        # VARIABLES
        # --------------------------------------------------------

        if line.startswith("VARIABLES"):

            vars_found = re.findall(r'"([^"]+)"', line)
            variables.extend([v.strip() for v in vars_found])

            i += 1

            while i < len(lines):

                l = lines[i].strip()

                if l.startswith('"'):
                    variables.append(l.strip('" ').strip())
                    i += 1
                else:
                    break

            continue

        # --------------------------------------------------------
        # New Zone
        # --------------------------------------------------------

        if line.startswith("ZONE"):

            if current_data:
                datasets.append({
                    "params": current_params.copy(),
                    "data": current_data
                })

            current_params = {}
            current_data = []

            reading_data = True

            i += 1
            continue

        # --------------------------------------------------------
        # AUXDATA / DATASETAUXDATA
        # --------------------------------------------------------

        if line.startswith(("AUXDATA", "DATASETAUXDATA")):

            matches = re.findall(
                r'(?:AUXDATA|DATASETAUXDATA)\s+(\S+)\s*=\s*"\s*([^"]+)"',
                line
            )

            for name, value in matches:

                try:
                    current_params[name] = float(value)
                except ValueError:
                    # Ignore TIME strings etc.
                    pass

            i += 1
            continue

        # --------------------------------------------------------
        # Numerical Data
        # --------------------------------------------------------

        if reading_data:

            if (
                line == ""
                or line.startswith("ZONE")
                or line.startswith("End of Xyce")
            ):
                reading_data = False
                continue

            try:
                values = [float(v) for v in line.split()]
                current_data.append(values)
            except ValueError:
                pass

        i += 1

    # append last zone

    if current_data:
        datasets.append({
            "params": current_params.copy(),
            "data": current_data
        })

    return variables, datasets

def parse_complex(v):
    '''
    input: complex or real number as string
    Parse complex numbers and real numbers and purely imaginary numbers and returns a complex object.
    '''
    v = v.strip()

    # Case 1: real ± j imag
    match = re.match(
        r'^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
        r'([+-])j'
        r'(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)$', v)

    if match:
        real = float(match.group(1))
        imag = float(match.group(3))
        if match.group(2) == '-':
            imag = -imag
        return complex(real, imag)

    # Case 2: purely imaginary number (e.g. "3j", "-j2.5", "j", "-j")
    match = re.match(
        r'^([+-]?)j(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)?$', v)

    if match:
        sign = -1.0 if match.group(1) == '-' else 1.0
        imag_part = match.group(2)

        # Handle "j" or "-j" (implicit 1)
        imag = float(imag_part) if imag_part else 1.0
        return complex(0.0, sign * imag)

    # Case 3: purely real number
    return complex(float(v), 0.0)


def parse_dataset(file_path):
    '''
    return variables
    - indep_vars: list of independent variable names, in order of appearance
    - indep_values: list of lists of independent variable values, in same order as indep_vars
    - dep_vars: list of dependent variable names, in order of appearance
    - dep_data: dict mapping dependent variable name to list of values (complex or real)
    '''
    with open(file_path, 'r') as f:
        content = f.read()

    # --- Parse independent variables ---
    indep_pattern = re.findall(r"<indep\s+(\w+)\s+\d+>(.*?)</indep>", content, re.S)
    indep_vars = []
    indep_values = []

    for name, values in indep_pattern:
        vals = [float(v.strip()) for v in values.strip().split()]
        indep_vars.append(name)
        indep_values.append(vals)
    

    # --- Parse dependent variables ---
    dep_pattern = re.findall(r"<dep\s+(.+?)\s+(.+?)>(.*?)</dep>", content, re.S)

    dep_vars = []
    dep_data = {}

    for dep_name, deps, values in dep_pattern:
        dep_vars.append(dep_name.strip())

        raw_vals = values.strip().split()
        parsed_vals = []

        for v in raw_vals:
            parsed_vals.append(parse_complex(v))

        dep_data[dep_name.strip()] = parsed_vals

    return indep_vars, indep_values, dep_vars, dep_data

''' Here we put all components and sources in the schematic into a dict and place it in the ui. '''
def parse_schematic(filename: str, ui):
    INTERESTING_TYPES = {
        "R",
        "C",
        "L",
        "CAPQ",
        "INDQ",
        "LIB",
        "VDC",
        "VAC",
        "IDC",
        "IAC",
        "PAC"
    }

    EXCLUDED_TYPES = {
        "GND",
        "SPICELIB",
        "SPICEPAR",
    }

    params = {}
    spice_params = {}
    sweeps = {}
    xyce_sweeps = {}

    with open(filename) as f:
        lines = f.readlines()

    in_components = False

    for line in lines:
        line = line.strip()

        if line == "<Components>":
            in_components = True
            continue

        if line == "</Components>":
            break

        if not in_components or not line.startswith("<"):
            continue

        # remove enclosing <>
        content = line[1:-1]

        # split while respecting quoted strings
        tokens = re.findall(r'"[^"]*"|\S+', content)

        if not tokens:
            continue

        comp_type = tokens[0]

        # ---------------------------------------------------------
        # Ignore probes
        # ---------------------------------------------------------
        if "PROBE" in comp_type.upper():
            continue

        # ---------------------------------------------------------
        # Simulator directives
        # ---------------------------------------------------------
        if comp_type.startswith("."):

            # -----------------------------------------------------
            # Standard Qucs sweep
            # -----------------------------------------------------
            if comp_type.upper() == ".SW":
                active = tokens[2] == "1"

                if active:
                    param_name = tokens[13].strip('"')
                    start = tokens[15].strip('"')
                    stop = tokens[17].strip('"')

                    sweeps[param_name] = f"{start}-{stop}"

            # -----------------------------------------------------
            # Xyce script containing .STEP commands
            # -----------------------------------------------------
            elif (
                comp_type.upper() == ".XYCESCR"
                and getattr(ui, "filename_ext_FD", "") == ".txt.HB.FD.dat"
            ):

                # Respect activation flag
                active = tokens[2] == "1"
                if not active:
                    continue

                # Script is stored as one quoted token
                script = None
                for tok in tokens:
                    if tok.startswith('"') and tok.endswith('"'):
                        script = tok[1:-1]
                        break

                if script is not None:
                    # Convert escaped newlines into actual newlines
                    script = script.replace(r"\n", "\n")

                    # Match both:
                    #   .STEP LIN param start stop step
                    #   .STEP param start stop step
                    step_pattern = re.compile(
                        r'^\s*\.STEP\s+(?:LIN\s+)?(\S+)\s+(\S+)\s+(\S+)',
                        re.IGNORECASE | re.MULTILINE
                    )

                    for match in step_pattern.finditer(script):
                        param_name = match.group(1)
                        start = match.group(2)
                        stop = match.group(3)

                        xyce_sweeps[param_name] = f"{start}-{stop}"

            continue

        # ---------------------------------------------------------
        # SpicePar
        # ---------------------------------------------------------
        if comp_type.upper() == "SPICEPAR":
            expr = tokens[9].strip('"')

            if "=" in expr:
                name, value = expr.split("=", 1)
                spice_params[name] = value

            continue

        # ---------------------------------------------------------
        # Ignore unwanted components
        # ---------------------------------------------------------
        if comp_type.upper() in EXCLUDED_TYPES:
            continue

        if comp_type.upper() not in INTERESTING_TYPES:
            print(f"WARNING: Unknown component type: {comp_type}")
            continue

        # ---------------------------------------------------------
        # Check activation flag
        # ---------------------------------------------------------
        active = tokens[2] == "1"

        if not active:
            continue

        name = tokens[1]

        # ---------------------------------------------------------
        # LIB
        # ---------------------------------------------------------
        if comp_type.upper() == "LIB":
            model_name = tokens[11].strip('"')
            param_name = tokens[13].strip('"')

            params[name] = model_name
            params[param_name] = spice_params.get(param_name, param_name)

        # ---------------------------------------------------------
        # PAC
        # ---------------------------------------------------------
        elif comp_type.upper() == "PAC":
            value = tokens[13].strip('"')
            params[name] = value

        # ---------------------------------------------------------
        # Passives and sources
        # ---------------------------------------------------------
        else:
            value = tokens[9].strip('"')
            params[name] = value

    # -------------------------------------------------------------
    # Add all SpicePar definitions
    # -------------------------------------------------------------
    params.update(spice_params)

    # -------------------------------------------------------------
    # Xyce .STEP definitions override .SW definitions
    # -------------------------------------------------------------
    if (
        getattr(ui, "filename_ext_FD", "") == ".txt.HB.FD.dat"
        and xyce_sweeps
    ):
        sweeps.update(xyce_sweeps)

    # -------------------------------------------------------------
    # Apply active sweeps
    # -------------------------------------------------------------
    for param_name, sweep_range in sweeps.items():
        params[param_name] = sweep_range

    ui.sch_params = params


