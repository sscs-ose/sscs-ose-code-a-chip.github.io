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

#ifndef _INS_ROUTINES
#define _INS_ROUTINES

#include "sym_proto.h"
#include "heur_types.h"
#include "vrp_common_types.h"

int farthest_ins_from_to PROTO((heur_prob *p, _node *tour, int cost,
	  int from_size, int to_size, int starter, neighbor *nbtree, 
	  int *intour, int *last, route_data *route_info, int cur_route));
int nearest_ins_from_to PROTO((heur_prob *p, _node *tour, int cost,
	  int from_size, int to_size, int starter, neighbor *nbtree, 
	  int *intour, int *last, route_data *route_info, int cur_route));
int closest PROTO((neighbor *nbtree, int *intour, int *last));
void ni_insert_edges PROTO((heur_prob *p, int new_node, neighbor *nbtree,
	  int *intour,int *last, _node *tour, int cur_route));
int farthest PROTO((neighbor *nbtree, int *intour, int *last));
void fi_insert_edges PROTO((heur_prob *p, int new_node, neighbor *nbtree,
	  int *intour, int *last, _node *tour, int cur_route));
int insert_into_tour PROTO((heur_prob *p, _node *tour, int starter, int size,
          int new_node, route_data *route_info, int cur_route));
void starters PROTO((heur_prob *p, int *starter, route_data *route_info,
	  int start));

#endif
