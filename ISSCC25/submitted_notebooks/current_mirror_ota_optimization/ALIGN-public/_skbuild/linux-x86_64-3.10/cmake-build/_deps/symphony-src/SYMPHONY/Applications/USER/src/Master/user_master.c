/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY Branch, Cut, and Price Library.         */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
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

/* User include files */
#include "user.h"
#ifdef COMPILE_IN_TM
#ifdef COMPILE_IN_LP
/* fill these in for sequential compilation if needed. */
#ifdef COMPILE_IN_CG
/* fill these in for sequential compilation if needed. */
#endif
#ifdef COMPILE_IN_CP
/* fill these in for sequential compilation if needed. */
#endif
#endif
#endif

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
  printf("master [ -H ] [ -F file ] \n\n\t%s\n\t%s\n\t%s\n\t%s\n\n",
	 "-H: help (solver-specific switches)",
	 "-F model: model should be read in from file 'model'",
	 "          (MPS format is assumed unless -D is also present)",
	 "-D data: model is in AMPL format and data is in file 'data'");
}

/*===========================================================================*/

/*===========================================================================*\
 * Initialize user-defined data structures. This basically consists of 
 * allocating the memory. If you are using the default data structure,
 * nothing needs to be changed here.
\*===========================================================================*/

int user_initialize(void **user)
{
   /* Create the user's data structure and pass a pointer back to SYMPHONY. */
   user_problem *prob = (user_problem *) calloc(1, sizeof(user_problem));

   *user = prob;

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Parse the user options and read in parameters from the parameter file 
 * given on the command line
\*===========================================================================*/

int user_readparams(void *user, char *filename, int argc, char **argv)
{
   /* This code is just a template for customization. Uncomment to use.*/
#if 0
   FILE *f;
   char line[50], key[50], value[50], c, tmp;
   int i;
   /* This gives you access to the user data structure*/
   user_problem *prob = (user_problem *) user;
   user_parameters *par = &(prob->par);

   if (strcmp(filename, "")){
      if ((f = fopen(filename, "r")) == NULL){
	 printf("SYMPHONY: file %s can't be opened\n", filename);
	 return(USER_ERROR); /*error check for existence of parameter file*/
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
      };
   }
#endif
   
   return(USER_DEFAULT);
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
#if 0
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;
   user_parameters *par = &(prob->par);
   char *infile = par->infile;
   FILE *f = NULL;
   char line[MAX_LINE_LENGTH], key[50], value[50];

   /* Make sure the file exists and can be opened */
   if (!strcmp(infile, "")){
      printf("\nMpp I/O: No problem data file specified\n\n");
      exit(1);
   }
   
   if ((f = fopen(infile, "r")) == NULL){
      printf("Readparams: file %s can't be opened\n", infile);
      exit(1); /*error check for existence of parameter file*/
   }

   /* Here you can read in the data for the problem instance. For the default
      setup, the user should set the colnum and rownum here. */
   while(NULL != fgets(line, MAX_LINE_LENGTH, f)){  /*read in problem data*/
      strcpy(key, "");
      sscanf(line, "%s%s", key, value);
      if (strcmp(key, "colnum") == 0){ /* Read in the number of columns */
	 READ_INT_PAR(prob->colnum);
      }
      else if (strcmp(key, "rownum") == 0){ /* Read in the number of rows */
	 READ_INT_PAR(prob->rownum);
      }
   }

   fclose(f);
#endif
   
   return(USER_DEFAULT);
}
   
/*===========================================================================*/

/*===========================================================================*\
 * Here is where the heuristics are performed and an upper bound is calculated.
 * An upper bound can also be specified in the parameter file. This function
 * need not be filled in if no upper bounding is done.
\*===========================================================================*/

int user_start_heurs(void *user, double *ub, double *ub_estimate)
{
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;

   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * If graph drawing will be used, the user must initialize the drawing
 * window here. This function need not be filled in.
\*===========================================================================*/

int user_init_draw_graph(void *user, int dg_id)
{
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;

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
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;

   /* Since we don't know how to form a good set of base variables, we'll put all
      the variables in the extra set */

   /* Set the number of extra variables*/
   *extravarnum = prob->colnum;

#if 0
   /* This code is not really needed because this is the default, so it is 
      commented out and left for illustration. */

   /* Put all the variables in the extra set */
   vars = *extravars = (int *) malloc(varnum * ISIZE);
   for (i = 0; i < varnum; i++){
     vars[i] = i;
   }
#endif
   
   /* Set the number of rows in the initial formulation */
   *basecutnum = prob->rownum;

   /* The set of base variables will be empty */
   *basevarnum = 0;
   *basevars  = NULL;

   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Receive the feasible solution. Doesn't need to be filled in.
\*===========================================================================*/

int user_receive_feasible_solution(void *user, int msgtag, double cost,
				   int numvars, int *indices, double *values)
{
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;

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
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP) && defined (COMPILE_IN_CP)
   /* This is is the case when we are copying data directly because
      the CP is not running separately. The easiest thing to do here is just
      to use the same user data structure in both the master and the cut
      pool. Then this subroutine would simply consist of 
      
      *user_cp = user;

      Otherwise, this code should be virtually
      identical to that of user_receive_cp_data() in the CP process.*/

   *user_cp = user;
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_cp_data() in the CP process */
#endif
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Generally, this function is not needed but you might find some use
 * for it. Someone did :).
\*===========================================================================*/

int user_process_own_messages(void *user, int msgtag)
{
   /* This gives you access to the user data structure. */
   user_problem *prob = (user_problem *) user;

   switch (msgtag){
    case 0:
    default:
      fprintf(stderr, "\nMaster: unknown message type %i!!!\n\n", msgtag);
      exit(1);
   }

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
   return(USER_DEFAULT);
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
   user_problem *prob = (user_problem *) (*user);

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

