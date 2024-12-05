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

#ifndef _LOWER_BOUND_H
#define _LOWER_BOUND_H

#include "sym_proto.h"
#include "vrp_types.h"
#include "heur_types.h"
#include "lb_params.h"

void lower_bound PROTO((vrp_problem *vrp, lb_params *lb_par,
			heurs *lh, int ub, int jobs, int *tids, int *sent));

#endif
