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
#include <stdio.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_lp_u.h"

/* MATCH include files */
#include "user.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the LP process.
\*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must receive all of the data sent from
 * user_send_lp_data() and set up data structures. Note that this function is
 * only called if one of COMPILE_IN_LP or COMPILE_IN_TM is FALSE. For 
 * sequential computation, nothing is needed here.
\*===========================================================================*/

int user_receive_lp_data(void **user)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must create the initial LP relaxation for
 * each search node. Basically, this involves constructing the base matrix in 
 * column ordered format. See the documentation for an explanation of how to 
 * fill out this function.
\*===========================================================================*/

int user_create_subproblem(void *user, int *indices, MIPdesc *mip, 
			   int *maxn, int *maxm, int *maxnz)
{
   /* This code isn't needed anymore, since the model is fed in as a generic
      IP. It's been left here as an example of how to use this function. */
#if 0
   user_problem *prob = (user_problem *) user;
   int i, j, index;

   /* set up the inital LP data */

   mip->nz = 2 * mip->n;

   /* Estimate the maximum number of nonzeros */
   *maxm = 2 * mip->m;
   *maxn = mip->n;
   *maxnz = mip->nz + ((*maxm) * (*maxn) / 10);
   
   /* Allocate the arrays. These are owned by SYMPHONY after returning. */
   mip->matbeg  = (int *) malloc((mip->n + 1) * ISIZE);
   mip->matind  = (int *) malloc((mip->nz) * ISIZE);
   mip->matval  = (double *) malloc((mip->nz) * DSIZE);
   mip->obj     = (double *) malloc(mip->n * DSIZE);
   mip->lb      = (double *) calloc(mip->n, DSIZE);
   mip->ub      = (double *) malloc(mip->n * DSIZE);
   mip->rhs     = (double *) malloc(mip->m * DSIZE);
   mip->sense   = (char *) malloc(mip->m * CSIZE);
   mip->rngval  = (double *) calloc(mip->m, DSIZE);
   mip->is_int  = (char *) malloc(mip->n * CSIZE);
   
   /* Fill out the appropriate data structures -- each column has
      exactly two entries */
   index = 0;
   for (i = 0; i < prob->nnodes; i++) {
      for (j = i+1; j < prob->nnodes; j++) {
	 prob->node1[index] = i; /* The first node of assignment 'index' */
	 prob->node2[index] = j; /* The second node of assignment 'index' */
	 mip->obj[index] = prob->cost[i][j]; /* Cost of assignment (i, j) */
	 mip->is_int[index] = TRUE;
	 mip->matbeg[index] = 2*index;
	 mip->matval[2*index] = 1;
	 mip->matval[2*index+1] = 1;
	 mip->matind[2*index] = i;
	 mip->matind[2*index+1] = j;
	 mip->ub[index] = 1.0;
	 index++;
      }
   }
   mip->matbeg[mip->n] = 2 * mip->n;
   
   /* set the initial right hand side */
   for (i = 0; i < prob->nnodes; i++) {
      mip->rhs[i] = 1;
      mip->sense[i] = 'E';
   }

#endif
   return(USER_DEFAULT);
}      


/*===========================================================================*/

/*===========================================================================*\
 * This function takes an LP solution and checks it for feasibility. By 
 * default, SYMPHONY checks for integrality. If any integral solution for your 
 * problem is feasible, then nothing needs to be done here.
\*===========================================================================*/

int user_is_feasible(void *user, double lpetol, int varnum, int *indices,
		     double *values, int *feasible, double *objval, 
		     char branching, double *heur_solution)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, the user can specify a special routine for sending back the feasible
 * solution. This need not be used unless there is a special format the user
 * wants the solution in. For sequential computation, you can use this routine
 * to interpret and store the feasible solution whenever one is found.
\*===========================================================================*/

int user_send_feasible_solution(void *user, double lpetol, int varnum,
				int *indices, double *values)
{
   return(USER_DEFAULT);
}


/*===========================================================================*/

/*===========================================================================*\
 * This function graphically displays the current fractional solution
 * This is done using the Interactive Graph Drawing program, if it is used.
\*===========================================================================*/

int user_display_lp_solution(void *user, int which_sol, int varnum,
			     int *indices, double *values)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * You can add whatever information you want about a node to help you
 * recreate it. I don't have a use for it, but maybe you will.
\*===========================================================================*/

int user_add_to_desc(void *user, int *desc_size, char **desc)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Compare cuts to see if they are the same. We use the default, which
 * is just comparing byte by byte.
\*===========================================================================*/

int user_same_cuts(void *user, cut_data *cut1, cut_data *cut2, int *same_cuts)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function receives a cut, unpacks it, and adds it to the set of
 * rows to be added to the LP. Only used if cutting planes are generated.
\*===========================================================================*/

int user_unpack_cuts(void *user, int from, int type, int varnum,
		     var_desc **vars, int cutnum, cut_data **cuts,
		     int *new_row_num, waiting_row ***new_rows)
{
   /* This code isn't needed anymore, since the model is fed in as a generic
      IP. It's been left here as an example of how to use this function. */
#if 0
   user_problem *prob = (user_problem *) user;
   
   int i, j, nzcnt;
   int *nodes;
   int indices[3]; /* The indices of the variables in the cut */
   waiting_row **row_list;
   
   *new_row_num = cutnum;
   if (cutnum > 0)
      *new_rows =
	 row_list = (waiting_row **) calloc (cutnum, sizeof(waiting_row *));
   
   for (j = 0; j < cutnum; j++){
      row_list[j] = (waiting_row *) malloc(sizeof(waiting_row));
      switch (cuts[j]->type){
	 
      case TRIANGLE:
	 nodes = (int *) (cuts[j]->coef);
	 /* Compute the indices of the variables in the cut */
	 indices[0] = prob->index[nodes[0]][nodes[1]];
	 indices[1] = prob->index[nodes[1]][nodes[2]];
	 indices[2] = prob->index[nodes[0]][nodes[2]];
	 row_list[j]->matind = (int *) malloc(3 * ISIZE);
	 row_list[j]->matval = (double *) malloc(3 * DSIZE);
	 /* Check to se which variables in the cut are present */
	 for (nzcnt = 0, i = 0; i < varnum; i++){
	    if (vars[i]->userind == indices[0] ||
		vars[i]->userind == indices[1] ||
		vars[i]->userind == indices[2]){
	       row_list[j]->matval[nzcnt] = 1.0;
	       row_list[j]->matind[nzcnt++] = vars[i]->userind;
	    }
	 }
	 row_list[j]->nzcnt = 3;
	 break;

       default:
	 printf("Unrecognized cut type!\n");
      }
   }
#endif
   
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * If the user wants to fill in a customized routine for sending and receiving
 * the LP solution, it can be done here. For most cases, the default routines
 * are fine.
\*===========================================================================*/

int user_send_lp_solution(void *user, int varnum, var_desc **vars, double *x,
			  int where)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This routine does logical fixing of variables
\*===========================================================================*/

int user_logical_fixing(void *user, int varnum, var_desc **vars, double *x,
			char *status, int *num_fixed)
{
   *num_fixed = 0;

   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function generates the 'next' column. Only used for column generation.
\*===========================================================================*/

int user_generate_column(void *user, int generate_what, int cutnum,
			 cut_data **cuts, int prevind, int nextind,
			 int *real_nextind, double *colval, int *colind,
			 int *collen, double *obj, double *lb, double *ub)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * You might want to print some statistics on the types and quantities
 * of cuts or something like that.
\*===========================================================================*/

int user_print_stat_on_cuts_added(void *user, int rownum, waiting_row **rows)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * You might want to eliminate rows from the local pool based on
 * knowledge of problem structure.
\*===========================================================================*/

int user_purge_waiting_rows(void *user, int rownum, waiting_row **rows,
			    char *delete_rows)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * The user might want to generate cuts in the LP using information
 * about the current tableau, etc. This is for advanced users only.
\*===========================================================================*/

int user_generate_cuts_in_lp(void *user, LPdata *lp_data, int varnum,
			     var_desc **vars, double *x,
			     int *new_row_num, cut_data ***cuts)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free all the user data structures
\*===========================================================================*/

int user_free_lp(void **user)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

