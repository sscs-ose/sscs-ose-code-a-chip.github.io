/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* Capacitated Network Routing Problems.                                     */
/*                                                                           */
/* (c) Copyright 2000-2013 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _CNRP_ROUTINES_H
#define _CNRP_ROUTINES_H

/* SYMPHONY include files */
#include "sym_proto.h"

/* CNRP include files */
#include "cnrp_types.h"

int is_same_edge PROTO((const void *ed0, const void *ed1));
void delete_dup_edges PROTO((small_graph *g));
void broadcast PROTO((cnrp_problem *cnrp, int *tids, int jobs));
void cnrp_create_variables PROTO((cnrp_problem *cnrp));
int *create_edge_list PROTO((cnrp_problem *cnrp, int *varnum,
			     char which_edges));

#endif


