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

#ifndef _VRP_TYPES2_H
#define _VRP_TYPES2_H

/* SYMPHONY include files */
#include "sym_proto.h"

/* VRP include files */
#include "vrp_common_types.h"
#include "vrp_cg_params.h"
#include "vrp_lp_params.h"
#ifdef COMPILE_HEURS
#include "heur_params.h"
#include "lb_params.h"

/*---------------------------------------------------------------------------*\
 * Here we keep track of the computation time for the lower and upper
 * bounding procedures
\*---------------------------------------------------------------------------*/

typedef struct BD_TIMES{
   double ub_overhead; /*overhead time used doing the upper bounding*/
   double ub_heurtime; /*actual comp time spent doing the upper bounding*/
   double lb_overhead; /*overhead time spent doing the lower bounding*/
   double lb_heurtime; /*actual comp time spent doing the lower bounding*/
}bd_times;

/*---------------------------------------------------------------------------*\
 * The heurs structure is used to keep track of the various heuristic processes
 * which are currently running. The jobs field contains the number of processes
 * currently running. The tids field is an array containing the tid's of these
 * processes. 
\*---------------------------------------------------------------------------*/

typedef struct HEURS{
   int   jobs;
   int  *tids;
   char *finished;
   int  *starter;
}heurs;

/*---------------------------------------------------------------------------*\
 * Contains the tree correspoding to the best lower bound found using
 * lagrangian relaxation 
\*---------------------------------------------------------------------------*/

typedef struct LOW_BD{
   int *tree;
   edge_data *best_edges;
   double lower_bound;
}low_bd;

/*---------------------------------------------------------------------------*\
 * This structure contains the values of the time out parameters for
 * upper and lower bounding routines.
\*---------------------------------------------------------------------------*/

typedef struct TIME_OUT_PAR{
   int ub;
   int lb;
}time_out_par;
#endif

/*__BEGIN_EXPERIMENTAL_SECTION__*/
/*---------------------------------------------------------------------------*\
 * Here we store the names of the executables to be used for each part of the
 * code. This way, we can run different versions of each part of the code
 * simply by changing the parameter file
\*---------------------------------------------------------------------------*/

typedef struct EXEC{
   char winprog[MAX_FILE_NAME_LENGTH];
#ifdef COMPILE_HEURS
   char heuristics[MAX_FILE_NAME_LENGTH];
#endif
}exec;

/*---------------------------------------------------------------------------*\
 * This structure contains debugging parameters for PVM. If they are zero,
 * then no debugging window comes up when the process is spawned. If any of
 * them are set at 4, then a debugging window for that process will be
 * launched on the host machine. 0 and 4 are the only two meaningful values
\*---------------------------------------------------------------------------*/

 typedef struct DEBUGGING{
   int winprog;
   int heuristics; 
}debugging;
/*___END_EXPERIMENTAL_SECTION___*/

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

#ifndef COMPILE_HEURS
typedef struct CLOSENODE{ /*close node to a particular one */
   int node;
   int cost;
}closenode;
#endif

typedef struct VRP_PARAMS{
   char          infile[MAX_FILE_NAME_LENGTH + 1];
   int           verbosity;
   char          tsp_prob;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   char          bpp_prob;
   /*___END_EXPERIMENTAL_SECTION___*/
   int           k_closest;
   int           min_closest;
   int           max_closest;
   int           add_all_edges;
   int           add_depot_edges;
   int           base_variable_selection;
   int           use_small_graph;
   char          small_graph_file[MAX_FILE_NAME_LENGTH];
   int           colgen_strat[2];
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   exec          executables;
   debugging     debug;
   /*___END_EXPERIMENTAL_SECTION___*/
#ifdef COMPILE_HEURS
   int          *rand_seed;
   int           tours_to_keep;
   time_out_par  time_out;
   int           do_heuristics;
#endif

   int           test;   
   char          test_dir[MAX_FILE_NAME_LENGTH +1]; /* Test files directory */ 
}vrp_params;

/*---------------------------------------------------------------------------*\
 * The problem data structure contains the data for a problem instance, as
 * well as some of the tours that have been generated.
\*---------------------------------------------------------------------------*/

typedef struct VRP_PROBLEM{
   char            name[100];  /* the name of the problem instance */
   vrp_params      par;
   vrp_cg_params   cg_par;
   vrp_lp_params   lp_par;
#ifdef COMPILE_HEURS
   heur_params     heur_par;
   lb_params       lb_par;
#endif
   int             dg_id;     /* drawgraph process id */
   int             vertnum;   /* the number of nodes in the problem, including
				 the depot */
   int             edgenum;   /* number of edges in the problem */
   int            *edges;
   int             numroutes; /* contains the number of routes that the problem
				 is to be solved with. can be prespecified. */
   int             depot;     /* the index of the depot, usually 1 */
   int             capacity;  /* the capacity of a truck */
   int            *demand;    /* an array containing the demands for each node.
				 node i's demand is p->demand[i-1] */
   int            *posx;      /* x coordinate for display purposes */
   int            *posy;      /* y coordinate for display purposes */
  
   distances       dist;      /* the data about the distances in the problem */

   best_tours     *cur_tour;  /* temporary tour storage */
#ifdef COMPILE_HEURS
   best_tours     *tours;     /* an array of the best tours found */
   int            *tourorder; /* a binary tree containing the ordering of the
				 tours in best_tours */
   int             tournum;   /* the number of tours stored in best_tours-1 */
   low_bd         *lb;        /* contains the information on the best lower
				 bound */
#endif
   small_graph    *g;         /* contains the edge data for the reduced graph*/
#if defined(CHECK_CUT_VALIDITY) || defined(TRACE_PATH)
   int             feas_sol_size;
   int            *feas_sol;
#endif
#ifdef COMPILE_HEURS
   bd_times        bd_time;
#endif
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   int             sol_pool_col_num;
   int            *sol_pool_cols;
   /*___END_EXPERIMENTAL_SECTION___*/
   int            *zero_vars;
   int             zero_varnum;
}vrp_problem;

#endif
