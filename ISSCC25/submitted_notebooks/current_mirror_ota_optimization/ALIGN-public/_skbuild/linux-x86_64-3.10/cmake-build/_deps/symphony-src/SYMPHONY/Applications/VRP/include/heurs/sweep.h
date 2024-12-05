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

#ifndef SWEEP_H
#define SWEEP_H

#include <math.h>
#include <stdlib.h>

#include "heur_types.h"
#include "heur_common.h"
#include "sym_constants.h"
#include "heur_routines.h"

typedef struct SWEEP_DATA{
   float angle;
   int cust;
}sweep_data;


void make_tour PROTO((heur_prob *p, sweep_data *data, best_tours *final_tour));

void sweep PROTO((int parent, heur_prob *p));

#endif
