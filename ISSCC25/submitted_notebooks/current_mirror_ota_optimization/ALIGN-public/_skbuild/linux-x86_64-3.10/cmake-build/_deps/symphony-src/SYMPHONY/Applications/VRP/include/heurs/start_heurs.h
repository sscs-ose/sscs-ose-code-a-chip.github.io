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

#ifndef _START_HEURS_H
#define _START_HEURS_H

#include "vrp_const.h"
#include "sym_proto.h"
#include "vrp_types.h"
#include "heur_types.h"
#include "lb_types.h"

void start_heurs PROTO((vrp_problem *vrp, heur_params *heur_par,
			lb_params *lb_par, double *ub, char no_windows));

#endif
