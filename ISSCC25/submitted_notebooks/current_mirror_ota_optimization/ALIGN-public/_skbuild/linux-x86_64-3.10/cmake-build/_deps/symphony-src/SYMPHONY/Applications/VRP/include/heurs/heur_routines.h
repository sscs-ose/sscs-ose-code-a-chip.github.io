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

#ifndef _HEUR_ROUTINES_H
#define _HEUR_ROUTINES_H

#include "sym_proto.h"
#include "heur_types.h"
#include "lb_types.h"

int receive PROTO((heur_prob *p));
void send_tour PROTO((_node *tour, int cost, int numroutes, int algorithm, 
		      double cpu_time, int parent, int vertnum,
		      int routes, route_data *route_info));
void free_heur_prob PROTO((heur_prob *p));
void free_lb_prob PROTO((lb_prob *p));

#endif
