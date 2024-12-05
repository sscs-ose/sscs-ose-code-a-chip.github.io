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

#ifndef _CNRP_CONST_H
#define _CNRP_CONST_H

#define LENGTH 255
#define KEY_NUM 41
#define DEAD 2
#define NEAR_INS -1
#define FAR_INS -2
#define DEPOT_PENALTY 20
#define RRR 6378.388
#define MY_PI 3.141592
#define LINE_LEN 80

/*---------------- problem types --------------------------------------------*/
#define NONE      0
#define VRP       1
#define TSP       2
#define BPP       3
#define CSTP      4
#define CTP       5

/*---------------- distance types -------------------------------------------*/
#define _EXPLICIT 0
#define _EUC_2D   1
#define _EUC_3D   2
#define _MAX_2D   3
#define _MAX_3D   4
#define _MAN_2D   5
#define _MAN_3D   6
#define _CEIL_2D  7
#define _GEO      8
#define _ATT      9

/*---------------- message types --------------------------------------------*/
#define CNRP_DATA        1
#define DISPLAY_DATA     2
#define NUMROUTES        3
#define COORD_DATA       4

/*---------------- cut types ------------------------------------------------*/
#define SUBTOUR_ELIM_SIDE       0
#define SUBTOUR_ELIM_ACROSS     1
#define SUBTOUR_ELIM            2
#define CLIQUE                  3
#define FLOW_CAP                4
#define X_CUT                   5
#define TIGHT_FLOW              6
#define MIXED_DICUT             7
#define OPTIMALITY_CUT_FIXED    8
#define OPTIMALITY_CUT_VARIABLE 9

/*---------------- tsp cut routines -----------------------------------------*/

#define NO_TSP_CUTS    0
#define SUBTOUR        1
#define BLOSSOM        2
#define COMB           4
#define ALL_TSP_CUTS   7

#define NUM_RANDS 6

#define ACTIVE_NODE_LIST_BLOCK_SIZE 100
#define DELETE_POWER 3
#define DELETE_AND 0x07

/*-------------- base variable selection rules ------------------------------*/
#define EVERYTHING_IS_EXTRA 0
#define SOME_ARE_BASE       1
#define EVERYTHING_IS_BASE  2

/*--------- constants used in creating the edges lists for the root ---------*/
#define CHEAP_EDGES      0
#define REMAINING_EDGES  1

/*--------- constants for saving the small graph ----------------------------*/
#define SAVE_SMALL_GRAPH 1
#define LOAD_SMALL_GRAPH 2

/*--------- constants for defining which set of exchange heuristics to do --*/     
#define FIRST_SET        1
#define SECOND_SET       2

#endif
