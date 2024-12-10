/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* Capacitated Network Routing Problems.                                     */
/*                                                                           */
/* (c) Copyright 2000-2013 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _CUT_GEN_USER_PARAMS_H
#define _CUT_GEN_USER_PARAMS_H

/* which_connected_routine choices */
#define CONNECTED    0
#define BICONNECTED  1
#define BOTH         2

typedef struct CG_USER_PARAMS{
   int            verbosity;
   char           prob_type;
   int            do_greedy;
   int            greedy_num_trials;
   int            do_extra_in_root;
   int            which_tsp_cuts;
   int            which_connected_routine;
   int            max_num_cuts_in_shrink;
   int            generate_x_cuts;
   int            generate_cap_cuts;
   int            generate_tight_cap_cuts;
   /*for minimumn cut*/
   int            do_mincut;
   int            do_extra_checking;
   int            update_contr_above;
   int            shrink_one_edges;
   double         tau;
}cnrp_cg_params;

#endif
