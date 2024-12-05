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

#ifndef _HEUR_TYPES_H
#define _HEUR_TYPES_H

#include "vrp_common_types.h"
#include "heur_params.h"

typedef struct NEIGHBOR{ /* a neighbor to a set of nodes */
   int nbor;    /* the index of the neighbor */
   int host;    /* the node in the set st. host-nbor edge is the cheapest */
   int cost;    /* the cost of that cheapest edge */
}neighbor;

typedef struct CLOSENODE{ /*close node to a particular one */
   int node;
   int cost;
}closenode;

/*---------------------------------------------------------------------------*\
| Contains the problem data needed by the upper bounding procedures           |
\*---------------------------------------------------------------------------*/

typedef struct HEUR_PROB{
   best_tours   *cur_tour;  /*temporary tour storage*/
   heur_params   par;       /*problem parameters*/
   int           vertnum;   /*the number of nodes in the problem,*\
			   \*including the depot                */
   int           numroutes; /*contains the number of routes that the*\
			   | problem is to be solved with. can be   |
			   \*prespecified.                         */
   int           depot;
   int           capacity;  /*the capacity of a truck*/
   int          *demand;    /*an array containing the demands for *\
			   | each node. node i's demand is        |
			   \*p->demand[i-1]                      */
   int           edgenum;  /*number of edges in the problem*/
   distances     dist;     /*contains the information for computing the costs*/
}heur_prob;

#endif



