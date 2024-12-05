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

#ifndef _VRP_CP_H
#define _VRP_CP_H

/* SYMPHONY include files */
#include "sym_proto.h"

typedef struct VRP_CP_PROBLEM{
   int vertnum;         /*number of vertices in the problem*/
   int edgenum;         /*number of edges in the problem*/
   int *edges;          /*a list of the edges (by index pairs)*/
   struct POOL_NET *n;
}vrp_cp_problem;

/*--------------------------------------------------------------------------*
 * The next three data structuires are used in the construction of the        
 * solution graph which we use to check the violation of certain cuts         
 *--------------------------------------------------------------------------*/

typedef struct POOL_NET{
   struct POOL_NODE *verts;
   struct POOL_EDGE *adjlist;
   int vertnum;
   int edgenum;
}pool_net;

typedef struct POOL_NODE{
   struct POOL_EDGE *first;
}pool_node;

typedef struct POOL_EDGE{
   struct POOL_EDGE *next;
   int other_end;
   double weight;
}pool_edge;

pool_net *create_pool_net PROTO((vrp_cp_problem *vcp, int varnum, int *indices,
				 double *values));
void free_pool_net PROTO((vrp_cp_problem *vcp));


#endif
