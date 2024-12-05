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

#ifndef _RECEIVE_ROUT_H
#define _RECEIVE_ROUT_H

#include "sym_proto.h"
#include "vrp_types.h"

double receive_tours PROTO((vrp_problem *vrp, heurs *hh, int *last, char print,
			    char routes, char add_edges, char win, int jobs,
			    int *sent));
double receive_lbs PROTO((vrp_problem *vrp, heurs *hh, char win, 
			  int numroutes, int jobs, int *sent));

#endif
