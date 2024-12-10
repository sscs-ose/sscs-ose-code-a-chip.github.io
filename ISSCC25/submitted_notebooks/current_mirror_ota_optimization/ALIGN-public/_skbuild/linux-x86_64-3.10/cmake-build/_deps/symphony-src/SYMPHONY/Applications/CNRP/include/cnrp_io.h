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

#ifndef _CNRP_IO_H
#define _CNRP_IO_H

/* SYMPHONY include files */
#include "sym_proto.h"

/* CNRP include files */
#include "cnrp_types.h"

void cnrp_readparams PROTO((cnrp_problem *cnrp, char *filename, int argc,
		       char **argv));
void cnrp_io PROTO((cnrp_problem *cnrp, char *infile));

#endif
