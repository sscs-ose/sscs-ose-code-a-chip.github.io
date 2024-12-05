/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2013 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _SPP_CONSTANTS_H_
#define _SPP_CONSTANTS_H_

/* stats on these functions */
#define READ_INPUT          0
#define FIX_LEX             1

/* input formats -- this tells how to decode the info in the input file */
#define OUR_FORMAT    5
#define OUR_FORMAT_0  0

/* feasibility of the problem */
#define SPP_OPTIMAL                3
#define SPP_FEASIBILITY_NOT_KNOWN  2
#define SPP_FEASIBLE               1
#define SPP_INFEASIBLE             0

#define ETOL 0.00001

#endif
   



