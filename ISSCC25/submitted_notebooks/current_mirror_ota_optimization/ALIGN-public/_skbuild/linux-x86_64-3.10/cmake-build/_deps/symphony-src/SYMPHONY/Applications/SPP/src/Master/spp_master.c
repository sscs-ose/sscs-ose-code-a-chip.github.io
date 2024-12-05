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
#include <stdlib.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_proccomm.h"
#include "sym_master_u.h"

/* SPP include files */
#include "spp.h"
#include "spp_common.h"
#include "spp_master_functions.h"

/*===========================================================================*\
 * This file contains stubs for the user-written functions for the master 
 * process. The primary function that has to be filled in here is user_io(),
 * where the data for the instance is read in and the user data structure
 * that stores the instance data filled out (this data structure is defined 
 * in user.h). Other than that, the default routines should work fine.
\*===========================================================================*/

/*===========================================================================*/

/*===========================================================================*\
 * This function gives help on command-line switches defined by the user.
 * All user switches have capital letters by convention.
\*===========================================================================*/

void user_usage(void){
         printf("master [ -H ] [ -F file ] \n\t%s\n\t%s\n",
		"-H: help (user switches)",
		"-F file: problem instance data is in 'file'");
}

/*===========================================================================*/

/*===========================================================================*\
 * Initialize user-defined data structures. This basically consists of 
 * allocating the memory. If you are using the default data structure,
 * nothing needs to be changed here.
\*===========================================================================*/

int user_initialize(void **user)
{
   spp_problem *spp = (spp_problem *) calloc(1, sizeof(spp_problem));

   *user = spp;

   spp->par = (spp_parameters *) calloc(1, sizeof(spp_parameters));
   spp->stat = (statistics *) calloc(2, sizeof(statistics));

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Parse the user options Read in parameters from the parameter file given on the command line
\*===========================================================================*/

int user_readparams(void *user, char *filename, int argc, char **argv)
{
   char c, tmp;
   int i;
   /* This gives you access to the user data structure*/
   spp_problem *spp = (spp_problem *) user;
   spp_parameters *par = spp->par;
   
   spp_read_params(spp, filename);

   spp_print_params(spp);

   /* Here you can parse the command line for options. By convention, the
      users options should be capital letters */

   for (i = 1; i < argc; i++){
      sscanf(argv[i], "%c %c", &tmp, &c);
      if (tmp != '-')
	 continue;
      switch (c) {
       case 'H':
	 user_usage();
	 exit(0);
	 break;
       case 'F':
	 strncpy(par->infile, argv[++i], MAX_FILE_NAME_LENGTH);
	 break;
       case 'T':
	 par->test = TRUE;
	 if(i+1 < argc){
	   sscanf(argv[i+1], "%c", &tmp);
	   if(tmp != '-'){
	     strncpy(par->test_dir, argv[++i],MAX_FILE_NAME_LENGTH);
	   }
	 }
	 break;
      };
   }

   return(USER_NO_PP);
}

/*===========================================================================*/

/*===========================================================================*\
 * Read in the data file, whose name was given in the parameter file.
 * This file contains instance data. Right now, this function is set up to 
 * read in just the number of columns and number of rows from the file.
 * Add more data as needed to describe the instance and set up the LP
 * relaxation.
\*===========================================================================*/

int user_io(void *user)
{
   /* This gives you access to the user data structure. */
   spp_problem *spp = (spp_problem *) user;
   int colnum, rownum;

   spp_read_input(spp);

   colnum = spp->cmatrix->colnum;
   rownum = spp->cmatrix->rownum;
   spp->cmatrix->active_colnum = colnum;
   spp->cmatrix->col_deleted = (char *) calloc(colnum/BITSPERBYTE + 1, CSIZE);
   spp->feasibility = SPP_FEASIBILITY_NOT_KNOWN;
   spp->feas_sol = (int *) malloc(rownum * ISIZE);

   /* order cols into lex ascending order */
   spp_fix_lex(spp);
   
   return(USER_SUCCESS);
}
   
/*===========================================================================*/

/*===========================================================================*\
 * Here is where the heuristics are performed and an upper bound is calculated.
 * An upper bound can also be specified in the parameter file. This function
 * need not be filled in if no upper bounding is done.
\*===========================================================================*/

int user_start_heurs(void *user, double *ub, double *ub_estimate)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * If graph drawing will be used, the user must initialize the drawing
 * window here. This function need not be filled in.
\*===========================================================================*/

int user_init_draw_graph(void *user, int dg_id)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This is the subroutine where the user specifies which variables are to be
 * in the base set and which variables are to be active in the root node but
 * not in the base set (these are called the "extra variables"). This is done
 * by listing the indices of the corresponding variables in arrays named
 * "basevars" and extravars below.
 *
 * The base set of variables form the core that is never removed from the LP
 * relaxation. Extra variables, on the other hand, can be removed if they are
 * fixed by reduced cost or by logic-based rules. Allowing the removal of
 * variables from the relaxation can lead to efficiencies, but there is a
 * price to pay in terms of extra bookkeeping. If possible, it is a good idea
 * to form a base set of variables consisting of those that are "likely" to be
 * present in some optimal solution. If this is not possible, the simplest
 * approach is just to put all the variables in the extra set, which allows
 * them all to be fixed by reduced cost if possible. This is implemented below
 * as an example.
 *
 * Note that each variable must have a unique user index by which the variable
 * can be identified later. Note also that it is possible to have variables
 * that are neither in the base set or active in the root node by using column
 * generation and filling out the function user_generate_column().
\*===========================================================================*/

int user_initialize_root_node(void *user, int *basevarnum, int **basevars,
			      int *basecutnum, int *extravarnum, int **extravars,
			      char *obj_sense, double *obj_offset,
			      char ***colnames, int *colgen_strat)
{
   /* This gives you access to the user data structure. */
   spp_problem *spp = (spp_problem *) user;
   int i;
   int *vars, varnum;

   /* Since we don't know how to form a good set of base variables, we'll put
      all the variables in the extra set */
   
   /* Set the number of extra variables*/
   varnum = *extravarnum = spp->cmatrix->colnum;
 
   /* Put all the variables in the extra set */
   vars = *extravars = (int *) malloc(varnum * ISIZE);
   for (i = 0; i < varnum; i++){
     vars[i] = i;
   }

   /* Set the number of rows in the initial formulation */
   *basecutnum = spp->cmatrix->rownum;

   /* The set base variables will be empty */
   *basevarnum = 0;
   *basevars  = NULL;

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Receive the feasible solution. Doesn't need to be filled in.
\*===========================================================================*/

int user_receive_feasible_solution(void *user, int msgtag, double cost,
				   int numvars, int *indices, double *values)
{
   spp_problem *spp = (spp_problem *)user;
   int *colnames = spp->cmatrix->colnames;
   int i;

   /* by default we are sent the user indices of nonzero variables.
      choose PACK_NONZEROS in user_pack_feasible_solution in LP. */

   if (spp->feasibility == SPP_FEASIBLE && cost >= spp->feas_value)
      return(USER_SUCCESS);

   spp->feasibility = SPP_FEASIBLE;
   spp->feas_value = cost;
   spp->feas_sol_length = numvars;
   for (i = 0; i < numvars; i++)
      spp->feas_sol[i] = colnames[indices[i]];

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we send the necessary data to the LP process. Notice that
 * there are two cases to deal with. If the LP or the TM are running
 * as separate processes, then we have to send the data by
 * message-passing. Otherwise, we can allocate the user-defined LP data
 * structure here and simply copy the necessary information. This is the
 * only place the user has to sorry about this distinction between
 * configurations. If running sequentially and using the default data
 * structure, nothing needs to be modified in here.
\*===========================================================================*/

int user_send_lp_data(void *user, void **user_lp)
{
   /* This gives you access to the user data structure. */
   spp_problem *spp = (spp_problem *) user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP)
   /* This is is the case when we are copying data directly because the LP is
      not running separately. The easiest thing to do here is just to use the
      same user data structure in both the master and the LP. Then this
      subroutine would simply consist of the line
      
      *user_lp = user;

      Otherwise, this code should be virtually
      identical to that of user_receive_lp_data() in the LP process.*/

   *user_lp = spp;
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_lp_data() in the LP process */

   col_ordered *m = spp->cmatrix;
   
   send_char_array((char *)spp->par, sizeof(spp_parameters));
   send_int_array(&m->colnum, 1);
   send_int_array(&m->rownum, 1);
   send_int_array(&m->nzcnt, 1);
   send_int_array(m->colnames, m->colnum);
   send_dbl_array(m->obj, m->colnum);
   send_int_array(m->matbeg, (m->colnum + 1));
   send_char_array((char *)m->matind, m->nzcnt * sizeof(row_ind_type));
   
#endif

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we send the necessary data to the CG process. Notice that
 * there are two cases to deal with. If the CG, LP, or the TM are running
 * as separate processes, then we have to send the data by
 * message-passing. Otherwise, we can allocate the user-defined LP data
 * structure here and simply copy the necessary information. This is the
 * only place the user has to sorry about this distinction between
 * configurations. If running sequentially and using the default data
 * structure, nothing needs to be modified in here.
\*===========================================================================*/

int user_send_cg_data(void *user, void **user_cg)
{
   return(USER_DEFAULT);   
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we send the necessary data to the CP process. Notice that
 * there are two cases to deal with. If the CP, LP, or the TM are running
 * as separate processes, then we have to send the data by
 * message-passing. Otherwise, we can allocate the user-defined LP data
 * structure here and simply copy the necessary information. This is the
 * only place the user has to sorry about this distinction between
 * configurations. If running sequentially and using the default data
 * structure, nothing needs to be modified in here.
\*===========================================================================*/

int user_send_cp_data(void *user, void **user_cp)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Generally, this function is not needed but you might find some use
 * for it. Someone did :).
\*===========================================================================*/

int user_process_own_messages(void *user, int msgtag)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This is the user's chance to display the solution in whatever
 * manner desired. 
\*===========================================================================*/

int user_display_solution(void *user, double lpetol, int varnum,
			  int *indices, double *values, double objval)
{
   spp_problem *spp = (spp_problem *)user;
   int *colnames = spp->cmatrix->colnames;
   int i;

   printf("\nBest Solution Found:\n");
   for (i = 0; i < varnum; i++)
      printf("%i \n", colnames[indices[i]]);
   printf("\n\n\n");
   
   return(USER_NO_PP);
}
   
 /*===========================================================================*/

 /*===========================================================================*\
  * This is a debugging feature which might
  * allow you to find out why a known feasible solution is being cut off.
 \*===========================================================================*/

 int user_send_feas_sol(void *user, int *feas_sol_size, int **feas_sol)
 {
 #ifdef TRACE_PATH

 #endif
    return(USER_DEFAULT);
 }   

 /*===========================================================================*/

 /*===========================================================================*\
  * This function frees everything.
 \*===========================================================================*/

 int user_free_master(void **user)
 {
    spp_problem *spp = (spp_problem *) (*user);

    FREE(spp->feas_sol);
    spp_free_cmatrix(spp->cmatrix);
    FREE(spp->cmatrix);
    if(!spp->par->test){
      FREE(spp->par);
      FREE(spp->stat);
      FREE(*user);
    }
    return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function is used to lift the user created cuts during warm starting *
/*===========================================================================*/

int user_ws_update_cuts (void *user, int *size, char **coef, double * rhs, 
			 char *sense, char type, int new_col_num, 
			 int change_type)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/





