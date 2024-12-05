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

#ifndef _LB_TYPES_H
#define _LB_TYPES_H

#include "vrp_common_types.h"
#include "lb_params.h"

/*---------------------------------------------------------------------------*\
| Contains the problem data needed by the lower bounding procedures           |
\*---------------------------------------------------------------------------*/

typedef struct LB_PROB{
  lb_params     par;       /*problem parameters*/
  int          vertnum;   /*the number of nodes in the problem,*\
			   \*including the depot                */
  int          edgenum;
  int          numroutes; /*contains the number of routes that the*\
			   | problem is to be solved with. can be   |
			   \*prespecified.                         */
  int          depot;     /*the index of the depot, usually 1*/
  int           capacity;  /*the capacity of a truck*/
  int         *demand;    /*an array containing the demands for *\
			   | each node. node i's demand is        |
			   \*p->demand[i-1]                      */
  distances     dist;      /*contains the information for computing the costs*/
  int           window;    /*contains the tid of the graphics window*/

}lb_prob;

#endif
