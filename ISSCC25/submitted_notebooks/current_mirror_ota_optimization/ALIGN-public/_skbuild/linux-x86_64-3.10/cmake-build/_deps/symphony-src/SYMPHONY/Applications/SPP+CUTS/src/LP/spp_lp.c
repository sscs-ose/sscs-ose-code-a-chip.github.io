/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2007 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdio.h>
#include <memory.h>

/* SYMPHONY include files */
#include "sym_proccomm.h"
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_lp_u.h"

/* SPP include files */
#include "spp_common.h"
#include "spp_lp.h"
#include "spp_lp_functions.h"

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
   spp_lp_problem *spp;
   col_ordered *m;
   int colnum, info;

   spp = (spp_lp_problem *) calloc(1, sizeof(spp_lp_problem));
   *user = spp;

   spp->par = (spp_lp_params *) calloc(1, sizeof(spp_lp_params));
   
   receive_char_array((char *)spp->par, sizeof(spp_lp_params));
   m = spp->cmatrix = (col_ordered *) calloc(1, sizeof(col_ordered));
   receive_int_array(&m->colnum, 1);
   colnum = m->active_colnum = m->colnum;
   receive_int_array(&m->rownum, 1);
   receive_int_array(&m->nzcnt, 1);
   m->colnames = (int *) malloc(colnum * ISIZE);
   m->col_deleted = (char *) calloc(colnum/BITSPERBYTE + 1, CSIZE); /*calloc!*/
   m->obj = (double *) malloc(colnum * DSIZE);
   m->matbeg = (int *) malloc((colnum + 1) * ISIZE);
   m->matind = (row_ind_type *) malloc(m->nzcnt * sizeof(row_ind_type));
   receive_int_array(m->colnames, colnum);
   receive_dbl_array(m->obj, colnum);
   receive_int_array(m->matbeg, (colnum + 1));
   receive_char_array((char *)m->matind, m->nzcnt * sizeof(row_ind_type));
   
   /* initialize some data structures in spp */
   spp_init_lp(spp);

   return(USER_SUCCESS);
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
   spp_lp_problem *spp = (spp_lp_problem *) user;
   col_ordered *cm = spp->cmatrix;
   int i;

   mip->nz = cm->nzcnt;
   *maxn = mip->n;   /* note that the number of columns cannot increase */
   *maxm = 2 * mip->m;
   *maxnz = mip->nz + ((*maxm) * (*maxn) / 100);

   mip->matbeg = (int *) malloc((mip->n + 1) * ISIZE);
   mip->matind = (int *) malloc(mip->nz * ISIZE);
   mip->matval = (double *) malloc(mip->nz * DSIZE);
   mip->obj    = (double *) malloc(mip->n * DSIZE);
   mip->lb     = (double *) calloc(mip->n, DSIZE);
   mip->ub     = (double *) malloc(mip->n * DSIZE);
   mip->rhs    = (double *) malloc(mip->m * DSIZE);
   mip->sense  = (char *) malloc(mip->m * CSIZE);
   mip->rngval = (double *) malloc(mip->m * DSIZE);
   mip->is_int = (char *) calloc (mip->n, CSIZE);

   memcpy((char *) mip->matbeg, (char *) cm->matbeg, (cm->colnum+1) * ISIZE);  
   memcpy((char *) mip->obj, (char *) cm->obj, cm->colnum * DSIZE);      

   for (i = cm->nzcnt - 1; i >= 0; i--) {
      mip->matind[i] = cm->matind[i];   /* cannot memcpy b/c int vs. short */
      mip->matval[i] = 1.0;
   }

   for (i = mip->n - 1; i >= 0; --i){
      mip->ub[i] = 1.0;
      /* mip->lb[i] = 0.0; */ /* Set by calloc */
      mip->is_int[i] = TRUE;
   }
   
   for (i = mip->m - 1; i >= 0; --i) {
      mip->rhs[i] = 1.0;
      mip->sense[i] = 'E';
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
   /* note that names of variables in the current solution will not be
      displayed by the default option */
   return(which_sol == DISP_RELAXED_SOLUTION ? DISP_NOTHING : DISP_NZ_INT);
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
   spp_lp_problem *spp = (spp_lp_problem *)user;
   cut_data ***lifted_cuts;
   waiting_row *row;
   int i, j, count, new_cutnum, *lifted_cutnum;
   int one_row_only = TRUE;

#if 0
   disp_where_cut_is_from(from);
   /* display cuts -- just for debugging */
   for (j = 0; j < cutnum; j++)
      display_cut_in_lp(spp, cuts[j], -1);
#endif

#if 0
   /*FIXME: This doesn't work anymore because the user can't get the pointer to
     the LP and therefore can't get the dual solution. */
   if (!one_row_only && spp->par->do_lift_in_lp) {
      /* we lift each cut and convert the lifted cuts into rows */
      lifted_cuts = (cut_data ***) malloc(cutnum * sizeof(cut_data **));
      lifted_cutnum = (int *) malloc(cutnum * ISIZE);
      for (i = 0, new_cutnum = 0; i < cutnum; i++) {
	 lift_cut_in_lp(spp, from, varnum, vars, &cuts[i], &lifted_cutnum[i],
			&lifted_cuts[i]);
	 new_cutnum += lifted_cutnum[i];
      }

      /* allocate space for the rows */
      *new_rows = (waiting_row **) malloc(new_cutnum * sizeof(waiting_row *));
      /* convert the cuts into rows. count counts the new rows */
      for (i = 0, count = 0; i < cutnum; i++) {
	 for (j = 0; j < lifted_cutnum[i]; j++) {
	    row = (*new_rows)[count++] =
	       (waiting_row *) malloc(sizeof(waiting_row));
	    /* fields of row: cut, nzcnt, matind, matval, violation.
	       violation is not filled out here. */
	    cut_to_row(spp, varnum, vars, lifted_cuts[i][j], &row->nzcnt,
		       &row->matind, &row->matval);
	    row->cut = lifted_cuts[i][j];
	 }
	 FREE(lifted_cuts[i]);
      }
      FREE(lifted_cuts);
      *new_row_num = count;
   }else{
#endif
      /* derive one constraint from each cut */
      *new_rows = (waiting_row **) malloc(cutnum * sizeof(waiting_row *));
      for (i = 0; i < cutnum; i++) {
	 row = (*new_rows)[i] = (waiting_row *) malloc(sizeof(waiting_row));
	 /* fields of row: cut, nzcnt, matind, matval, violation.
	    violation is not filled out here. */
	 cut_to_row(spp, varnum, vars, cuts[i], &row->nzcnt, &row->matind,
		    &row->matval);
	 row->cut = cuts[i];
	 cuts[i] = NULL;
      }
      *new_row_num = cutnum;
#if 0
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
   /* Needed for cutting planes */
   return(where == LP_SOL_TO_CP ? SEND_NONZEROS : SEND_FRACTIONS);
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
   spp_lp_problem *spp = (spp_lp_problem *)(*user);

#ifndef COMPILE_IN_LP
   FREE(spp->par);
   spp_free_cmatrix(spp->cmatrix);
#endif
   spp_free_lp_tmp(spp);
   FREE(*user);

   return(USER_SUCCESS);

}

/*===========================================================================*/

