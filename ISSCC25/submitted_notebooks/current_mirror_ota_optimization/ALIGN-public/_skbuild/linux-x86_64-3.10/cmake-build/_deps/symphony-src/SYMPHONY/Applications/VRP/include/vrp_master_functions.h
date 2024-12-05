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

#ifndef _VRP_MASTER_FUNCTIONS_H
#define _VRP_MASTER_FUNCTIONS_H

/* SYMPHONY include files */
#include "sym_proto.h"

/* VRP include files */
#include "vrp_types.h"
#ifdef COMPILE_HEURS
#include "heur_types.h"
#include "lb_types.h"
#endif

int is_same_edge PROTO((const void *ed0, const void *ed1));
void delete_dup_edges PROTO((small_graph *g));
void broadcast PROTO((vrp_problem *vrp, int *tids, int jobs));
int *create_edge_list PROTO((vrp_problem *vrp, int *varnum, char which_edges));

#endif


