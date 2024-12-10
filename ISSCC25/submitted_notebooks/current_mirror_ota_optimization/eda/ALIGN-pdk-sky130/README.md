# ALIGN-pdk-sky130
## We are working to support [SKY130](https://github.com/google/skywater-pdk) with [ALIGN](https://github.com/ALIGN-analoglayout/ALIGN-public)

## Getting started

### Step 1: Install ALIGN
Install ALIGN following instructions on [ALIGN GitHub Repository](https://github.com/ALIGN-analoglayout/ALIGN-public)

### Step 2: Clone the ALIGN PDK Sky130 source code to your local environment
```console
$ git clone https://github.com/ALIGN-analoglayout/ALIGN-pdk-sky130
```

### Step 3: Run ALIGN with Sky130
You may run the align tool using a simple command line tool named `schematic2layout.py`
For most common cases, you will simply run:
```console
$ schematic2layout.py <NETLIST_DIR> -p <PDK_DIR> 
```

For instance, to build the layout for five_transistor_ota. First make a directory in ALIGN-public (in this example `work`), thereafter, use `schematic2layout.py`: 
```console
$ cd ALIGN-public
$ mkdir work && cd work
$ schematic2layout.py ../ALIGN-pdk-sky130/examples/five_transistor_ota -p ../ALIGN-pdk-sky130/SKY130_PDK/
```

