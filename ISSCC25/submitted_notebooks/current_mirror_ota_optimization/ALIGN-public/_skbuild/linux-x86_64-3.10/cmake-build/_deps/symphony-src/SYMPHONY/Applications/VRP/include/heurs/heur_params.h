/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/* This file was modified by Ali Pilatin January, 2005 (alp8@lehigh.edu)     */
/*                                                                           */
/* (c) Copyright 2000-2005 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _HEUR_PARAMS_H
#define _HEUR_PARAMS_H

/*--------------------------------------------------------------------*\
| This data structure contains parameters used to run the two savings  |
| routines. savings_trials and savings2_trials contain the number of   |
| "blocks" of trialss of each of these two heuristics that should be   |
| spawned. The only difference between these two heuristics is that    |
| savings2 uses binomial heaps and is slightly faster on most          |
| problems. Also, they break ties differently. Mu and lamda are the    |
| two parameters used in determining the savings for each node. As we  |
| vary these parameters, we get different solutions. The grid size     |
| specifies what size search grid of parameter settings we should try  |
| for each "block" of trials. If there is more than one block of       |
| trials to be executed, then the first one uses far_insert to begin   |
| each new route and the second one uses random insertion              |
\*--------------------------------------------------------------------*/

typedef struct SAVINGS_PARAM{
   int savings_trials;
   int savings2_trials;
   int grid_size;
   float mu;
   float lamda;
}savings_param;

/*--------------------------------------------------------------------*\
| This structure contains parameters relating to the construction of   |
| TSP tours by various simple heuristics and to the partitioning of    |
| them into VRP solutions                                              |
\*--------------------------------------------------------------------*/

typedef struct TSP_PAR{
   int ni_trials;
   int fi_trials;
   int fini_trials;
   int num_starts;
}tsp_par;

/*--------------------------------------------------------------------*\
| This structure contains the values of the parameters for all the     |
| heuristics. See the README file for an explanation of the parameters |
\*--------------------------------------------------------------------*/

typedef struct HEUR_PARAMS{
  int    no_of_machines;
  int    sweep_trials;
  savings_param   savings_par;
  savings_param   savings3_par;
  int    near_cluster_trials;
  int    route_opt1;
  int    route_opt2;
  int    route_opt3;
  int    exchange;
  int    exchange2;
  float  fini_ratio;
  int    ni_trials;
  int    fi_trials;
  int    fini_trials;
  tsp_par         tsp;
}heur_params;

#endif
