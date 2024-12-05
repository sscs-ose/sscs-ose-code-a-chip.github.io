/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Matching Problem.                                                     */
/*                                                                           */
/* (c) Copyright 2005-2008 Michael Trick and Ted Ralphs. All Rights Reserved.*/
/*                                                                           */
/* This application was originally written by Michael Trick and was modified */
/* by Ted Ralphs (ted@lehigh.edu)     .                                      */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _USER_H
#define _USER_H

#include "sym_master.h"
#include "sym_macros.h"

#define MAXNODES 200

/*---------------------------------------------------------------------------*\
 * Use this data structure to store the value of any run-time parameters.
\*---------------------------------------------------------------------------*/

typedef struct USER_PARAMETERS{
   /* Name of file containingthe instance data */
   char             infile[MAX_FILE_NAME_LENGTH + 1];
   int              test;
   char             test_dir[MAX_FILE_NAME_LENGTH +1]; /* Test files directory */
}user_parameters;
/*---------------------------------------------------------------------------*\
 * Use this data structure to store the instance data after it is read in.
\*---------------------------------------------------------------------------*/

typedef struct USER_PROBLEM{
   user_parameters  par;        /* the parameters */
   /* Number of nodes */
   int		    numnodes;
   /* Cost of matching i and j */
   int		    cost[MAXNODES][MAXNODES];
   /* match1[k] is the first component of the assignment with index k */
   int		    match1[MAXNODES*(MAXNODES-1)/2];
   /* match2[k] is the first component of the assignment with index k */
   int		    match2[MAXNODES*(MAXNODES-1)/2]; 
   /* index[i][j] is the index of the variable assoc. w/ matching i and j */
   int              index[MAXNODES][MAXNODES];
}user_problem;


int match_read_data PROTO((user_problem *prob, char *infile));
int match_load_problem PROTO((sym_environment *env, user_problem *prob));

#endif
