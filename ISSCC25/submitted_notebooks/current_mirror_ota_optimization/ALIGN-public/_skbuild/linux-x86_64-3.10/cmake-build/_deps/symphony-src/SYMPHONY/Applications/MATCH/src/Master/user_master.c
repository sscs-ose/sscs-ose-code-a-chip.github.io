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
#include <stdlib.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_master_u.h"

/* MATCH include files */
#include "user.h"

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
   /* Don't need this */
#if 0
   user_problem *prob = (user_problem *) calloc(1, sizeof(user_problem));
   
   *user = prob;
#endif 
   
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Parse the user options and read in parameters from the parameter file 
 * given on the command line
\*===========================================================================*/

int user_readparams(void *user, char *filename, int argc, char **argv)
{

   FILE *f;  
   char line[50], key[50], value[50], c, tmp;
   int i;

   /* This gives you access to the user data structure*/
   user_problem *prob = (user_problem *) user;
   user_parameters *par = &(prob->par);

   /* This code is just a template for customization. Uncomment to use.*/

#if 0

   if (strcmp(filename, "")){
      if ((f = fopen(filename, "r")) == NULL){
	 printf("SYMPHONY: file %s can't be opened\n", filename);
	 exit(1); /*error check for existence of parameter file*/
      }
      
      /* Here you can read in the parameter settings from the file. See the 
	 function bc_readparams() for an example of how this is done. */
      while(NULL != fgets(line, MAX_LINE_LENGTH, f)){  /*read in parameters*/
	 strcpy(key, "");
	 sscanf(line, "%s%s", key, value);
	 
	 if (strcmp(key, "input_file") == 0){
	    par->infile[MAX_FILE_NAME_LENGTH] = 0;
	    strncpy(par->infile, value, MAX_FILE_NAME_LENGTH);
	 }
      }      
      
      fclose(f);
   }
#endif 
   
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

   return(USER_SUCCESS);
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
   /* This code is just a template for customization. Uncomment to use.*/
 # if 0
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;
   user_parameters *par = &(prob->par);
   char *infile = par->infile;
   FILE *f = NULL;
   int i, j;

   if ((f = fopen(infile, "r")) == NULL){
      printf("Readparams: file %s can't be opened\n", infile);
      return(USER_ERROR); /*error check for existence of parameter file*/
   }

   /* Read in the costs */
   fscanf(f,"%d",&(prob->nnodes));
   for (i = 0; i < prob->nnodes; i++)
      for (j = 0; j < prob->nnodes; j++)
	 fscanf(f, "%d", &(prob->cost[i][j]));
   
   prob->colnum = (prob->nnodes)*(prob->nnodes-1)/2;
   prob->rownum = prob->nnodes;

#endif
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
			      int *basecutnum, int *extravarnum,
			      int **extravars, char *obj_sense,
			      double *obj_offset, char ***colnames,
			      int *colgen_strat)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Receive the feasible solution. Doesn't need to be filled in.
\*===========================================================================*/

int user_receive_feasible_solution(void *user, int msgtag, double cost,
				   int numvars, int *indices, double *values)
{
   return(USER_DEFAULT);
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
   user_problem *prob = (user_problem *) user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP)
   /* This is is the case when we are copying data directly because the LP is
      not running separately. The easiest thing to do here is just to use the
      same user data structure in both the master and the LP. Then this
      subroutine would simply consist of the line
      
      *user_lp = user;

      Otherwise, this code should be virtually
      identical to that of user_receive_lp_data() in the LP process.*/

   *user_lp = user;
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_lp_data() in the LP process */
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
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP) && defined (COMPILE_IN_CG)
   /* This is is the case when we are copying data directly because
      the CG is not running separately. The easiest thing to do here is just
      to use the same user data structure in both the master and the cut
      generator. Then this subroutine would simply consist of 
      
      *user_cg = user;

      Otherwise, this code should be virtually
      identical to that of user_receive_cg_data() in the CG process.*/

   *user_cg = user;
#ifdef CHECK_CUT_VALIDITY
   /* Send the feasible solution here */
#endif
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_cg_data() in the CG process */
#ifdef CHECK_CUT_VALIDITY
   /* Send the feasible solution here */
#endif
#endif
   return(USER_SUCCESS);
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
 * manner desired. A return value of USER_DEFAULT will cause the
 * default solution display routine to be executed, even if the user displays
 * the solution as well.
\*===========================================================================*/

int user_display_solution(void *user, double lpetol, int varnum, int *indices,
			  double *values, double objval)
{
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;
   int index;
 
   for (index = 0; index < varnum; index++){
      if (values[index] > lpetol) {
	 printf("%2d matched with %2d at cost %6d\n",
		prob->match1[indices[index]],
		prob->match2[indices[index]],
		prob->cost[prob->match1[indices[index]]]
		[prob->match2[indices[index]]]);
      }	   
   }
   
   return(USER_SUCCESS);
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
   user_problem *prob = (user_problem *) calloc(1, sizeof(user_problem));

   FREE(prob);

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




