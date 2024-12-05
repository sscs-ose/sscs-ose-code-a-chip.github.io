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

#ifndef _CNRP_LP_H
#define _CNRP_LP_H

#define COMPILING_FOR_LP

/* SYMPHONY include files */
#include "sym_types.h"

/* CNRP include files */
#include "cnrp_lp_params.h"
#include "cnrp_common_types.h"
#include "network.h"

#define BEST_K                                         0
#define VARS_CLOSEST_TO_HALF                           1
#define DEPOTS_CLOSEST_TO_HALF                         2
#define DEPOTS_CLOSEST_TO_HALF_BRANCH_RIGHT            3
#define VARS_CLOSEST_TO_HALF_PREFER_DEPOT              4
#define DEPOTS_AT_HALF_BRANCH_RIGHT                    5
#define DEPOTS_AT_HALF                                 6
#define VARS_AT_HALF_PREFER_DEPOT_BRANCH_RIGHT         7
#define VARS_AT_HALF_PREFER_DEPOT                      8
#define VARS_CLOSEST_TO_HALF_PREFER_DEPOT_BRANCH_RIGHT 9
#define VARS_AT_HALF                                   10

typedef struct POS_WEIGHT_LHS{
   int position;
   double lhs;
}p_w_l;

/*---------------------------------------------------------------------------*\
| This is the data structure used to store the edges in the 1-edges graph     |
| used the logical fixing routine                                             |
\*---------------------------------------------------------------------------*/

typedef struct LP_NET_EDGE{
   struct LP_NET_EDGE *next;
   int other_end;
}lp_net_edge;

/*---------------------------------------------------------------------------*\
| Another data structure used to store the 1-edges graph                      |
\*---------------------------------------------------------------------------*/

typedef struct LP_NET_NODE{
   lp_net_edge *first;
   int degree;
   int comp;
   double demand;
   char scanned;
}lp_net_node;

/*---------------------------------------------------------------------------*\
| This is where the 1-edges graph is actually stored                          |
\*---------------------------------------------------------------------------*/

typedef struct LP_NET{
   lp_net_node *verts;
   lp_net_edge *adjlist;
   int vertnum;
   int edgenum;
}lp_net;

/*---------------------------------------------------------------------------*\
| Here we store the specific data needed to process each node of the tree     |
\*---------------------------------------------------------------------------*/

typedef struct CNRP_SPEC{
   cnrp_lp_params par;
   int            window;    /*contains the tid of the graphics window*/
   int            vertnum;   /*the number of nodes in the problem,
			       including the depot                */
   double        *demand;    /*a list of the customer demands*/
   double         capacity;  /*the capacity of the trucks*/
   int            numroutes; /*contains the number of routes that the problem
			       is to be solved with. can be prespecified.  */
   double         utopia_fixed;
   double         utopia_variable;
   int           *edges;     /*contains a list of the edges in the current
			       subproblem*/
   int           *costs;     /*contains the objective function values*/
   _node         *cur_sol;
   int           *cur_sol_tree;
   double         variable_cost;
   double         fixed_cost;
   double         ub;
}cnrp_spec;

/*---------------------------------------------------------------------------*\
| Routines entirely specific to main_lp                                       |
\*---------------------------------------------------------------------------*/

lp_net *create_lp_net PROTO((cnrp_spec *cnrp, char *status, int edgenum,
			     var_desc **vars));
int cnrp_lp_connected PROTO((lp_net *n, double *compdemands));
void free_lp_net  PROTO((lp_net *n));
char construct_feasible_solution PROTO((cnrp_spec *cnrp, network *n,
				       double *objval, double etol,
				       char branch));
double compute_lhs PROTO((int number,  int *indices, double *values,
			  cut_data *cut, int vertnum));

#endif
