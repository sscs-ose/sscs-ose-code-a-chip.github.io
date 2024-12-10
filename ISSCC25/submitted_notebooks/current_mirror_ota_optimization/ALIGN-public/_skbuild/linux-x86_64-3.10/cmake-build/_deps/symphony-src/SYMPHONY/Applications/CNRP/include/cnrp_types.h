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

#ifndef _CNRP_TYPES_H
#define _CNRP_TYPES_H

/* SYMPHONY include files */
#include "sym_proto.h"

/* CNRP include files */
#include "cnrp_common_types.h"
#include "cnrp_cg_params.h"
#include "cnrp_lp_params.h"
#include "cnrp_cp_params.h"

/*---------------------------------------------------------------------------*\
 * The "small_graph" data structure is used to store the subset of the
 * edges that will be used initially in actually solving the problem. 
 * These edges usually consist of any edges found among the ones used in
 * the heuristics solutions and the set of shortest edges adjacent to
 * each node in the graph 
\*---------------------------------------------------------------------------*/

typedef struct SMALL_GRAPH{   /* this gets passed eg. to lin-kerninghan */
   int vertnum;               /* vertnum in the restricted (small) graph */
   int edgenum;               /* edgenum in the restricted (small) graph */
   int allocated_edgenum;
   int del_edgenum;
   edge_data *edges;       /* The data for these edges */
}small_graph;

typedef struct CLOSENODE{ /*close node to a particular one */
   int node;
   int cost;
}closenode;

typedef struct CNRP_PARAMS{
   char          infile[MAX_FILE_NAME_LENGTH + 1];
   int           verbosity;
   char          prob_type;
   int           k_closest;
   int           min_closest;
   int           max_closest;
   int           add_all_edges;
   int           add_depot_edges;
   int           base_variable_selection;
   int           use_small_graph;
   char          small_graph_file[MAX_FILE_NAME_LENGTH];
   int           colgen_strat[2];
#ifdef MULTI_CRITERIA
   double        binary_search_tolerance;
   double        compare_solution_tolerance;
#endif   
   int           test;
   char          test_dir[MAX_FILE_NAME_LENGTH +1];  /* Test files directory */
}cnrp_params;

/*---------------------------------------------------------------------------*\
 * The problem data structure contains the data for a problem instance, as
 * well as some of the tours that have been generated.
\*---------------------------------------------------------------------------*/

typedef struct CNRP_PROBLEM{
   char            name[100];  /* the name of the problem instance */
   cnrp_params      par;
   cnrp_cg_params  cg_par;
   cnrp_lp_params  lp_par;
   cnrp_cp_params  cp_par;
   int             dg_id;     /* drawgraph process id */
   int             vertnum;   /* the number of nodes in the problem, including
				 the depot */
   int             edgenum;   /* number of edges in the problem */
   int            *edges;
   int             numroutes; /* contains the number of routes that the problem
				 is to be solved with. can be prespecified. */
   int             depot;     /* the index of the depot, usually 1 */
   double          capacity;  /* the capacity of a truck */
   double         *demand;    /* an array containing the demands for each node.
				 node i's demand is p->demand[i-1] */
   int            *posx;      /* x coordinate for display purposes */
   int            *posy;      /* y coordinate for display purposes */
  
   distances       dist;      /* the data about the distances in the problem */

   best_tours     *cur_tour;  /* temporary tour storage */
   int            *cur_sol_tree;
   double          fixed_cost;
   double          variable_cost;
   double          utopia_fixed;
   double          utopia_variable;
   double          ub;
   small_graph    *g;         /* contains the edge data for the reduced graph*/
#if defined(CHECK_CUT_VALIDITY) || defined(TRACE_PATH)
   int             feas_sol_size;
   int            *feas_sol;
#endif
   int             basecutnum;
   int            *basevars;
   int             basevarnum;
   int            *extravars;
   int             extravarnum;
   int            *zero_vars;
   int             zero_varnum;
}cnrp_problem;

#endif
