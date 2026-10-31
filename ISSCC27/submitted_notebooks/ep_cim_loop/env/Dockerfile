# Image for ep_cim_loop.ipynb (Code-a-Chip, equilibrium-propagation chip): IIC-OSIC-TOOLS (Yosys, OpenROAD, Magic, Netgen, Xyce, Icarus Verilog, KLayout)
# + pinned Python packages (CPU PyTorch) + pinned SKY130 PDK + this package.
# Build (in the package folder):   docker build -t ep_cim_loop -f env/Dockerfile .
# Jupyter:                         docker run --rm -p 127.0.0.1:8888:8888 ep_cim_loop      -> http://localhost:8888/lab/tree/ep_cim_loop.ipynb
# Without Jupyter (one command):   docker run --rm -v "$PWD/out:/home/designer/out" ep_cim_loop \
#                                    python3 -m papermill ep_cim_loop.ipynb /home/designer/out/ep_cim_loop_out.ipynb -p MODE quick -p WORK /home/designer/out/work
FROM hpretl/iic-osic-tools:2026.10

USER root
# Same tool paths as the image's login profile (/etc/profile.d/iic-osic-tools-setup.sh), without its PYTHONPATH,
# so that the pinned packages in /opt/venv come before the image's own Python packages.
ENV TOOLS=/foss/tools \
    PATH=/opt/venv/bin:/foss/tools/bin:/foss/tools/klayout:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LD_LIBRARY_PATH=/foss/tools/klayout:/foss/tools/ngspice/lib:/foss/tools/iverilog/lib:/foss/tools/openems/lib:/foss/tools/kactus2:/foss/tools/gtkwave/lib/x86_64-linux-gnu:/foss/tools/kepler-formal/lib:/foss/tools/libman/lib \
    HOME=/home/designer \
    QT_QPA_PLATFORM=offscreen \
    PYTHONDONTWRITEBYTECODE=1

# Python packages (versions of the notebook results); the image's Jupyter is reused through --system-site-packages
COPY env/requirements.txt /tmp/requirements.txt
RUN python3 -m venv --system-site-packages /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# SKY130 PDK pinned to the open_pdks build used for the results (the image ships a newer sky130A in /foss/pdks).
# The scripts in src/ read it from ~/pdk/volare.
RUN /opt/venv/bin/volare enable --pdk sky130 --pdk-root /home/designer/pdk/volare c6d73a35f524070e85faff4a6a9eef49553ebc2b

# This package (notebook, src/, env/, weights/, results/); writable for any --user
COPY . /home/designer/ep_cim_loop
RUN chmod -R a+rwX /home/designer

WORKDIR /home/designer/ep_cim_loop
EXPOSE 8888
# The image's default entrypoint starts a VNC desktop; it is not needed here.
ENTRYPOINT []
CMD ["python3", "-m", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--IdentityProvider.token=", "--ServerApp.root_dir=/home/designer/ep_cim_loop"]
