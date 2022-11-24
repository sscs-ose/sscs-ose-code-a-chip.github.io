#!/bin/sh

if [ ! -f klayout*.deb ];
then
  wget https://www.klayout.org/downloads/Ubuntu-18/klayout_0.27.12-1_amd64.deb
fi


#sudo apt install -f libqt4-designer libqt4-xml libqt4-sql libqt4-network libqtcore4 libqtgui4
sudo dpkg -i klayout_0.27.12-1_amd64.deb


# dpkg: dependency problems prevent configuration of klayout:
#  klayout depends on libqt4-designer (>= 4.8.7); however:
#   Package libqt4-designer is not installed.
#  klayout depends on libqt4-xml (>= 4.8.7); however:
#   Package libqt4-xml is not installed.
#  klayout depends on libqt4-sql (>= 4.8.7); however:
#   Package libqt4-sql is not installed.
#  klayout depends on libqt4-network (>= 4.8.7); however:
#   Package libqt4-network is not installed.
#  klayout depends on libqtcore4 (>= 4.8.7); however:
#   Package libqtcore4 is not installed.
#  klayout depends on libqtgui4 (>= 4.8.7); however:
#   Package libqtgui4 is not installed.
#  klayout depends on libruby2.5 (>= 2.5.1); however:
#   Package libruby2.5 is not installed.
#  klayout depends on libpython3.6 (>= 3.6.5); however:
#   Package libpython3.6 is not installed.