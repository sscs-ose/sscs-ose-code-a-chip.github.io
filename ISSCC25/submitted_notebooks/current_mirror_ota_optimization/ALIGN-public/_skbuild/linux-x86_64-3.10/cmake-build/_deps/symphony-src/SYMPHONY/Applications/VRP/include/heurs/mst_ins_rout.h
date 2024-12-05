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

#ifndef _MST_INS_ROUT_H
#define _MST_INS_ROUT_H

#include "sym_proto.h"
#include "lb_types.h"
#include "heur_types.h"

int make_k_tree PROTO((lb_prob *p, int *tree, int *lamda, int k));
int closest PROTO((neighbor *nbtree, int *intree, int *last, int *host));
void ni_insert_edges PROTO((lb_prob *p, int new_node, neighbor *nbtree,
	int *intree, int *last, int *lamda, int mu));
int new_lamda PROTO((lb_prob *p, int upper_bound, int cur_bound, int *lamda,
	int numroutes, int *tree, edge_data *cur_edges, int alpha));

#endif
