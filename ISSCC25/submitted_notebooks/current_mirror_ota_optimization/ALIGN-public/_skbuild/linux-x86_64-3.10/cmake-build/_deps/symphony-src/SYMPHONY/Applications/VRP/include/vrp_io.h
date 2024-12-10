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

#ifndef _VRP_IO_H
#define _VRP_IO_H

/* SYMPHONY include files */
#include "sym_proto.h"

/* VRP include files */
#include "vrp_types.h"

void vrp_readparams PROTO((vrp_problem *vrp, char *filename, int argc,
		       char **argv));
void vrp_io PROTO((vrp_problem *vrp, char *infile));
void vrp_set_defaults PROTO((vrp_problem *vrp));
void vrp_create_instance PROTO((void *user, int vertnum, int numroutes,
				int capacity, int *demand, int *cost,
				small_graph *g) );

#endif
