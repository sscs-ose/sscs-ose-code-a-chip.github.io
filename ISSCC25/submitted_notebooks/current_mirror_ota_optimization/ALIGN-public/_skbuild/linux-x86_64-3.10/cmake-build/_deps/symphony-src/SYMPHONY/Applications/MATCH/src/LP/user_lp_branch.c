/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Matching Problem.                                                     */
/*                                                                           */
/* (c) Copyright 2005-2007 Michael Trick and Ted Ralphs. All Rights Reserved.*/
/*                                                                           */
/* This application was originally written by Michael Trick and was modified */
/* by Ted Ralphs (ted@lehigh.edu)     .                                      */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_lp_u.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the LP process related
 * to branching.
\*===========================================================================*/

/*===========================================================================*\
 * This function determines whether to branch. You can essentially
 * leave this up to SYMPHONY unless there is some compelling reason not to.
\*===========================================================================*/

int user_shall_we_branch(void *user, double lpetol, int cutnum,
			 int slacks_in_matrix_num, cut_data **slacks_im_matrix,
			 int slack_cut_num, cut_data **slack_cuts, int varnum,
			 var_desc **vars, double *x, char *status,
			 int *cand_num, branch_obj ***candidates,
			 int *action)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we select the branching candidates. This can essentially be
 * left to SYMPHONY too using one of the built-in functions, but here, I
 * demonstrate how to branch on cuts, which must be done by the user.
\*===========================================================================*/

int user_select_candidates(void *user, double lpetol, int cutnum,
			   int slacks_in_matrix_num,
			   cut_data **slacks_in_matrix, int slack_cut_num,
			   cut_data **slack_cuts, int varnum, var_desc **vars,
			   double *x, char *status, int *cand_num,
			   branch_obj ***candidates, int *action,
			   int bc_level)

{
   return(USER_DEFAULT);
}

/*===========================================================================*/

int user_compare_candidates(void *user, branch_obj *can1, branch_obj *can2,
			    double ub, double granularity,
			    int *which_is_better)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * You can let SYMPHONY choose which child to retain. The default is
 * to keep the one with the lower objective function value.
\*===========================================================================*/

int user_select_child(void *user, double ub, branch_obj *can, char *action)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, you can print out a more identifiable description of the
 * branching object than just "variable 51". 
\*===========================================================================*/

int user_print_branch_stat(void *user, branch_obj *can, cut_data *cut,
			   int n, var_desc **vars, char *action)
{
   return(USER_DEFAULT);
}
