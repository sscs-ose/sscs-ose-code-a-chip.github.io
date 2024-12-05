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

#ifndef _VRP_CG_PARAMS_H
#define _VRP_CG_PARAMS_H

/* which_connected_routine choices */
#define CONNECTED    0
#define BICONNECTED  1
#define BOTH         2

/*__BEGIN_EXPERIMENTAL_SECTION__*/
typedef struct COL_GEN_PARAMS{
   int  grid_size;
   float lambda;
   float mu;
}col_gen_params;

/*___END_EXPERIMENTAL_SECTION___*/
typedef struct VRP_CG_PARAMS{
   int            verbosity;
   char           tsp_prob;
   int            do_greedy;
   int            greedy_num_trials;
   int            do_extra_in_root;
   int            which_tsp_cuts;
   int            which_connected_routine;
   int            max_num_cuts_in_shrink;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   int            do_mincut;
   int            always_do_mincut;
   int            update_contr_above;
   int            shrink_one_edges;
   int            do_extra_checking;
   int            do_our_decomp;
#ifdef COMPILE_DECOMP
   int            max_num_columns;    /* to generate in bfm */
   int            generate_farkas_cuts;
   int            generate_no_cols_cuts;
   int            generate_capacity_cuts;
   int            allow_one_routes_in_bfm;
   int            follow_one_edges;
   col_gen_params col_gen_par;
#endif
#ifdef COMPILE_OUR_DECOMP
   int            do_decomp_once;
   int            decomp_decompose;
   int            feasible_tours_only; /* if set to 1,
					  generate only feasible tours */  
   float          graph_density_threshold; /* if density higher,
					      do not generate columns */
   float          gap_threshold;
#endif
   /*___END_EXPERIMENTAL_SECTION___*/
}vrp_cg_params;

#endif
