from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter
plt.style.use(Path(__file__).parent / "own.mplstyle")




fig, ax = plt.subplots()

xformatter = EngFormatter(unit='m')
ax.xaxis.set_major_formatter(xformatter)

yformatter = EngFormatter(unit='Ohm')
ax.yaxis.set_major_formatter(yformatter)

# Schematic: /home/matthi/QucsWorkspace/60_GHz_MPA_prj/rppd.sch
ax.plot(
    [0.0000001, 0.0000005,  0.000001,   0.000002,   0.000003,   0.000004,   0.000005,   0.000006,   0.000007,   0.000008,   0.000009,   0.00001,    0.00002,    0.00003,    0.00004,    0.0001],
    [3020,      648,        327,        164,        110,        82.3,       65.5,       54.9,       47.1,       41.2,       36.6,       33,         16.5,       11,         8.25,       3.3], # R
  # [301,       324,        327,        328,        330,        329.2       327.5,      329.9,      329.7,      329.6,      329.4,      330,        330,        330,        330,        330] # Rsheet=R*W/L
    label=f"L=1um",
    marker = 'o'
)

ax.set_title('Rppd, corner: res_typ')
ax.set_xlabel('W')
ax.set_ylabel('R')

ax.legend()

fig, ax = plt.subplots()
# ax.plot(
#     [0.0000001, 0.0000005,  0.000001,   0.000002,   0.000003,   0.000004,   0.000005,   0.000006,   0.000007,   0.000008,   0.000009,   0.00001,    0.00002,    0.00003,    0.00004,    0.0001],
#     [95.8,      199,        327,        584,        841,        1100,       1350,       1610,       1870,       2130,       2380,       2640,       5210,       7780,       10300,      25800], # R
#   # [958,       398,        327,        292,        280,        275,        270,        268,        267,        266.3,      264.4,      264,        261,        259.3,      257.5,      258] # Rsheet=R*W/L
#     label=f"W=1um"
# )

ax.plot(
    [0.0000001, 0.0000005,  0.000001,   0.000002,   0.000003,   ],
    [95.8,      199,        327,        584,        841,        ], # R
  # [958,       398,        327,        292,        280,        275,        270,        268,        267,        266.3,      264.4,      264,        261,        259.3,      257.5,      258] # Rsheet=R*W/L
    label=f"W=1um",
    marker = 'o'
)

ax.set_title('Rppd, corner: res_typ')
ax.set_xlabel('L')
ax.set_ylabel('R')



plt.show()