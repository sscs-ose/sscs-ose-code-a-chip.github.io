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

#ifndef _S_PATH_H
#define _S_PATH_H

#include "sym_proto.h"
#include "heur_types.h"

typedef struct ADJ_LIST{
  int custnum;
  int cost;
  struct ADJ_LIST *next;
}adj_list;

        int *sp PROTO((adj_list **adj, int numnodes, int origin, int dest));
        void make_routes PROTO((heur_prob *p, _node *tsp_tour, int start, 
				 best_tours *new_tour));

#endif
