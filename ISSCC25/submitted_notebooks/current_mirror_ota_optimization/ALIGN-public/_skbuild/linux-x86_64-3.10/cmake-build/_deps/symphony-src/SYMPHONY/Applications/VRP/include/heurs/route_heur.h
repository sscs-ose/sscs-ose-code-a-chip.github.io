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

#ifndef ROUTE_HEUR_H
#define ROUTE_HEUR_H 

#include "vrp_types.h"
#include "heur_types.h"

void route_heur PROTO((vrp_problem *vrp, heur_params *heur_par, 
		      heurs *rh, int trials, int jobs,  int *tids, 
		       int *sent, best_tours *solutions));

#endif
