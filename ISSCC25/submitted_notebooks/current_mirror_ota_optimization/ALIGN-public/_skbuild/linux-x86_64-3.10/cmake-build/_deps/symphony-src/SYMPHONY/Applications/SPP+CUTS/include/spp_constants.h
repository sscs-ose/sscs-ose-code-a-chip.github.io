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

/* possible values for starcl_which_node */
#define MIN_DEGREE     0
#define MAX_DEGREE     1
#define MAX_XJ_MAX_DEG 2

/* types of cuts */
#define CLIQUE                0
#define ODD_HOLE              1
#define ODD_ANTIHOLE          2
#define WHEEL                 3
#define GOMORY                4
#define ORTHOCUT              5
#define OTHER_CUT             6
#define CLIQUE_LIFTED        10
#define ODD_HOLE_LIFTED      11
#define ODD_ANTIHOLE_LIFTED  12

/* strategies for lifting cuts */
#define DONT_CHANGE_CUT   0
#define MAY_CHANGE_CUT    1

/* choices for which_atilde */
#define COLS_OF_A         0
#define SPARS_PATTERN     1
#define EDGE_NODE_INC     2
#define EDGE_NODE_INC_PERT 3

#endif
   



