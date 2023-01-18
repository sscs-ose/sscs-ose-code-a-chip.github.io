* Copyright 2022 GlobalFoundries PDK Authors
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     https://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.

*************************************************************************
** Global Parameter Settings
*************************************************************************
** NGSPICE include file for global switches, corner parameters
** and other user-defined settings
** **********************************************************************
** -------------------------------------------
** MonteCarlo and matching simulation setting:
** -------------------------------------------
** sw_stat_global
** sw_stat_mismatch
**
**   --------------------------------------------------------------------------
**   |       setting        |  sw_stat_global=0     |  sw_stat_global=1       |
**   --------------------------------------------------------------------------
**   |  sw_stat_mismatch=0  | No statistical        | Global variation is on, |
**   |                      |  modeling             | but mismatch is off.    |
**   --------------------------------------------------------------------------
**   |  sw_stat_mismatch=1  | mismacth is on,       | Most realistic          |
**   |                      | global variation off  | distribution.           |
**   --------------------------------------------------------------------------
**
**
**   (default) - sw_stat_global=1 and sw_stat_mismatch=1
**   This setting provides the most complete representation of the
**   statistical variations during chip manufacturing.
**   Global process variations are determined by random distributions.
**   Mismatch is differentiated from global variation in that mismatch only 
**   includes intra-die variation, and it is especially critical for analog matching applications.
**
**   mc_skew is the monte-carlo simulation variation control.
**
**
** -------------------------------------------
**       Flicker noise corner setting:
** -------------------------------------------
**
**        "fnoicor" switch is added for user to select between the best- or worst-case 
**         flicker noise simulation options
**         fnoicor = 0  : (default) as-extracted simulation
**         fnoicor = 1  : worst case simulation
**
** *****************************************************************************
**
** Switches
**
*********** Default mc switches **********
**
.param
+  sw_stat_global = 0
+  sw_stat_mismatch = 0
**
********* Default mc skew value *********
**
+ mc_skew = 3
+ res_mc_skew = 3
+ cap_mc_skew = 3
**
****** Default flicker noise corner switch *****
**
+  fnoicor = 0
********************************************************************************
