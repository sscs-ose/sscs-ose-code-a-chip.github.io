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

/* system include files */
#include <memory.h>
#include <stdio.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_cg_u.h"

/* MATCH include files */
#include "user.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains user-written functions used by the cut generator
 * process.
\*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must receive all of the data sent from
 * user_send_cg_data() and set up data structures. Note that this function is
 * only called if one of COMPILE_IN_CG, COMPILE_IN_LP, or COMPILE_IN_TM is
 * FALSE. For sequential computation, nothing is needed here.
\*===========================================================================*/

int user_receive_cg_data(void **user, int dg_id)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * If the user wants to fill in a customized routine for sending and receiving
 * the LP solution, it can be done here. For most cases, the default routines
 * are fine.
\*===========================================================================*/

int user_receive_lp_solution_cg(void *user)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Find cuts violated by a particular LP solution. This can be a fairly
 * involved function but the bottom line is that an LP solution comes in
 * and cuts go out. Remember, use the function cg_send_cut() to send cuts out
 * when they are found.
\*===========================================================================*/

int user_find_cuts(void *user, int varnum, int iter_num, int level,
		   int index, double objval, int *indices, double *values,
		   double ub, double etol, int *num_cuts, int *alloc_cuts, 
		   cut_data ***cuts)
{

#if 1
   
   /* Here, we demonstrate how to add an explicit cut that doesn't have a
      special packed form. This is the easiest way to add cuts, but may be
      inefficient in parallel. */

   user_problem *prob = (user_problem *) user;
   double edge_val[200][200]; /* Matrix of edge values */
   int i, j, k, cutind[3];
   double cutval[3];
   
   int cutnum = 0;

   /* Allocate the edge_val matrix to zero (we could also just calloc it) */
   memset((char *)edge_val, 0, 200*200*ISIZE);
   
   for (i = 0; i < varnum; i++) {
      edge_val[prob->match1[indices[i]]][prob->match2[indices[i]]] = values[i];
   }
   
   for (i = 0; i < prob->numnodes; i++){
      for (j = i+1; j < prob->numnodes; j++){
	 for (k = j+1; k < prob->numnodes; k++) {
	    if (edge_val[i][j]+edge_val[j][k]+edge_val[i][k] > 1.0 + etol) {
	       /* Found violated triangle cut */
	       /* Form the cut as a sparse vector */
	       cutind[0] = prob->index[i][j];
	       cutind[1] = prob->index[j][k];
	       cutind[2] = prob->index[i][k];
	       cutval[0] = cutval[1] = cutval[2] = 1.0;
	       cg_add_explicit_cut(3, cutind, cutval, 1.0, 0, 'L',
				   TRUE, num_cuts, alloc_cuts, cuts);
	       cutnum++;
	       
	    }
	 }
      }
   }
   
#else
   /* Here, we show how to use a user-defined cut class with a packed form. In
      this case, the packed form is just to store the three nodes that form
      the triangle. See the function user_unpack_cuts() for the code to unpack
      the cut. */
   user_problem *prob = (user_problem *) user;
   double edge_val[200][200]; /* Matrix of edge values */
   int i, j, k;
   int *new_cuts;
   cut_data cut;
   int coef[3];
   
   int cutnum = 0;

   /* Allocate the edge_val matrix to zero (we could also just calloc it) */
   memset((char *)edge_val, 0, 200*200*ISIZE);
   
   for (i = 0; i < varnum; i++) {
      edge_val[prob->match1[indices[i]]][prob->match2[indices[i]]] 
	 = values[i];
   }
   for (i = 0; i < prob->numnodes; i++){
      for (j = i+1; j < prob->numnodes; j++){
	 for (k = j+1; k < prob->numnodes; k++) {
	    if (edge_val[i][j]+edge_val[j][k]+edge_val[i][k] > 1.0 + etol) {
	       memset(new_cuts, 0, prob->numnodes * ISIZE);
	       coef[1] = i; 
	       coef[2] = j;
	       coef[3] = k;
	       cut.size = 3*ISIZE;
	       cut.coef = (char *) coef;
	       cut.rhs = 1.0;
	       cut.range = 0.0;
	       cut.type = TRIANGLE;
	       cut.sense = 'L';
	       cut.deletable = TRUE;
	       cut.branch = ALLOWED_TO_BRANCH_ON;
	       cg_add_user_cut(&cut, num_cuts, alloc_cuts, cuts);
	       cutnum++;
	       
	    }
	 }
      }
   }
   
   FREE(new_cuts);
#endif
   
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free the user data structure. If the default setup is used with sequential
 * computation, nothing needs to be filled in here.
\*===========================================================================*/

int user_free_cg(void **user)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This is an undocumented (for now) debugging feature which can allow the user
 * to identify the cut which cuts off a particular known feasible solution.
\*===========================================================================*/

#ifdef CHECK_CUT_VALIDITY
int user_check_validity_of_cut(void *user, cut_data *new_cut)
{
  return(USER_DEFAULT);
}
#endif
