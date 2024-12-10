/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* (c) Copyright 2000-2013 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _VRP_LP_PARAMS_H
#define _VRP_LP_PARAMS_H

/*---------------------------------------------------------------------------*\
 * Here we store the vrp specific data needed to process each node of the tree
\*---------------------------------------------------------------------------*/

typedef struct VRP_LP_PARAMS{
   int    verbosity;
   int    branching_rule;
   int    detect_tailoff; /* 1  indicates tailing-off detection is desirable */
   float  child_compar_obj_tol;
   int    branch_on_cuts;
   int    strong_branching_cand_num_max;
   int    strong_branching_cand_num_min;
   int    strong_branching_red_ratio;
}vrp_lp_params;

#endif
