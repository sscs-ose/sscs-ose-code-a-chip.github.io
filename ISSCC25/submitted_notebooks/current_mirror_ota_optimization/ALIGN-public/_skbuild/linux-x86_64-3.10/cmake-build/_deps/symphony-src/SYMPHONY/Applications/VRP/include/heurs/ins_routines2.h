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

#ifndef _INS_ROUTINES2_H
#define _INS_ROUTINES2_H

#include "sym_proto.h"
#include "heur_types.h"
#include "vrp_common_types.h"

void nearest_ins2 PROTO((
          heur_prob *p, _node *tour, route_data *route_info, int from_size, 
          int to_size, neighbor *nbtree, int *intour, int *last, int *zero_cost));
int closest2 PROTO(( neighbor *nbtree, int *intour, int *last, int *host));
void ni_insert_edges2 PROTO((
	  heur_prob *p, int new_node, neighbor *nbtree, int *intour, int *last,
	  _node *tour, route_data *route_info));
int insert_into_tour2 PROTO((
          heur_prob *p, _node *tour, int new_node, route_data *route_info));
void new_host2 PROTO((
	  heur_prob *p, int node, neighbor *nbtree, int *intour, int *last,
	  _node *tour, route_data *route_info, int *zero_cost));
void seeds2 PROTO((
	  heur_prob *p, int *numroutes, int *intour, neighbor *nbtree));
void farthest_ins_from_to2 PROTO((
	  heur_prob *p, _node *tour, int from_size, 
	  int to_size, neighbor *nbtree, 
	  int *intour, int *last));
int farthest2 PROTO((
	  neighbor *nbtree, int *intour, int *last));
void fi_insert_edges2 PROTO((
	  heur_prob *p, int new_node, neighbor *nbtree, int *intour, int *last));

#endif
