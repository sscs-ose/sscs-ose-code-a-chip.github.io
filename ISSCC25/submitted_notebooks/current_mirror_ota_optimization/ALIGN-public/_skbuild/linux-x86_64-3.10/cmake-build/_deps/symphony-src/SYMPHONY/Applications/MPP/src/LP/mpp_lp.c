/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Mixed Postman Problem.                                                */
/*                                                                           */
/* (c) Copyright 2005-2007 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This application was originally developed by Andrew Hofmann and was       */
/* modified by  Ted Ralphs (ted@lehigh.edu)                                  */
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

/* MPP include files */
#include "mpp.h"

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
   mpp_problem *mpp = (mpp_problem *) user;

   int i, j, ind;

   /* set up the inital LP data */

   mip->nz = (6 * mpp->numedges)+ (2 * mpp->numarcs);
 
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
   mip->is_int = (char *) calloc(mip->n, CSIZE);
   
   for (i = 0, ind = 0; i < mip->n; i++){
      mip->matbeg[i] = ind;
      mip->is_int[i] = TRUE;
      /* indegree equals outdegree constraint */
      for (j = 0; j <= mpp->numnodes - 1; j++){
	 /* checks to see if node i is the start node of every edge arc */
	 if (mpp->head[i] == j){
	    mip->matind[ind] = j;
	    mip->matval[ind++] = 1;
	 }else if (mpp->tail[i] == j){
	    mip->matind[ind] = j;
	    mip->matval[ind++] = -1;
	 }
      }
      
      /* Now the constraint that each edge must be traversed at least once */
      if (i >= mpp->numarcs){ /* Check to see if it is an edge */
	 if (i < mpp->numarcs + mpp->numedges){
	    mip->matind[ind] = mpp->numnodes + i - mpp->numarcs;
	 }else{
	    mip->matind[ind] = mpp->numnodes + i - (mpp->numarcs +
						     mpp->numedges);
	 }
	 mip->matval[ind++] = 1;
	 /* mip->lb[i] = 0; */ /* Already set to zero from calloc */
	 mip->ub[i] = (double) (mpp->numarcs + mpp->numedges);
      }else{
	 mip->lb[i] = 1.0;
	 mip->ub[i] = (double) (mpp->numarcs + mpp->numedges);
      }
      mip->obj[i] = (double) (mpp->cost[i]);
   }
   mip->matbeg[i] = ind;
   
   /* set the initial right hand side */
   for (i = 0; i <= mpp->numnodes-1 ; i++){
      mip->rhs[i]   = 0;
      mip->sense[i] = 'E';
   }
   for (i = mpp->numnodes; i <= mpp->numnodes+mpp->numedges-1 ; i++){
      mip->rhs[i]   = 1;
      mip->sense[i] = 'G';
   }
   
   return(USER_SUCCESS);
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
   return(DISP_NZ_INT);
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
   mpp_problem *mpp = (mpp_problem *)user;
   int * node_checker;
   int * cut_holder=NULL;
   int edge_direction=0;
   int i, j, nzcnt = 0;
   waiting_row **row_list = NULL;
   int *matind = NULL;
   cut_data *cut;
   int rhs_count;
   char *coef;
   double *matval = NULL;
   *new_row_num = cutnum;
   node_checker= (int *) calloc(mpp->numnodes, sizeof(int));
  
   if (cutnum > 0)
      *new_rows = row_list = (waiting_row **) calloc (cutnum,
						      sizeof(waiting_row *));

   for (j = 0; j < cutnum; j++){
      coef = (cut = cuts[j])->coef;
      cut_holder = (int *) cut->coef;

      cuts[j] = NULL;
      (row_list[j] = (waiting_row *) malloc(sizeof(waiting_row)))->cut = cut;
      switch (cut->type){
       case ODD_CUT:
	 matind = (int *) malloc(varnum * ISIZE);
	 nzcnt = 0;
	 rhs_count = 0;
	 for (i = 0; i <= mpp->numnodes - 1; i++){
	    node_checker[i]=0;
	 }
	 /*make array for 1 if node is in cut, 0 if not*/
	 for (i = 0; i < (cut->size/4); i++){
	    node_checker[cut_holder[i]]=1;
	 }
	 for (i = 0; i <= varnum - 1; i++){
	    if (vars[i]->userind >= mpp->numarcs+mpp->numedges){
	       if (node_checker[mpp->tail[(vars[i]->userind)-mpp->numedges]]==1&&
		   node_checker[mpp->head[(vars[i]->userind)-mpp->numedges]]==0){
		  matind[nzcnt] = i;
		  nzcnt++;
		  rhs_count++;
	       }
	    }else if ((vars[i]->userind >= mpp->numarcs)){
	       if ((node_checker[mpp->tail[vars[i]->userind]] == 1 &&
		    node_checker[mpp->head[vars[i]->userind]] == 0)){
		  matind[nzcnt] = i;
		  nzcnt++;
		  rhs_count++;
	       }
	    }else if (node_checker[mpp->tail[vars[i]->userind]] == 1 &&
		      node_checker[mpp->head[vars[i]->userind]] == 0){
	       matind[nzcnt] = i;
	       nzcnt++;
	       rhs_count++;
	    } else if (node_checker[mpp->tail[vars[i]->userind]] == 0 &&
		       node_checker[mpp->head[vars[i]->userind]] == 1){
	       rhs_count++;
	    }
	 }
	 
	 row_list[j]->matind = matind =
	    (int *) realloc((char *)matind, nzcnt*ISIZE);
	 cut->rhs=(rhs_count+1)/2;
	 row_list[j]->nzcnt = nzcnt;
	 row_list[j]->matval = matval = (double *) malloc(nzcnt * DSIZE);
	 for (i = nzcnt-1; i >= 0; i--)
	    matval[i] = 1;
	 cut->branch = ALLOWED_TO_BRANCH_ON;
	 break;	
	 
   	 
       default:
	 printf("Unrecognized cut type!\n");
      }
   }
   FREE(node_checker);
   
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

