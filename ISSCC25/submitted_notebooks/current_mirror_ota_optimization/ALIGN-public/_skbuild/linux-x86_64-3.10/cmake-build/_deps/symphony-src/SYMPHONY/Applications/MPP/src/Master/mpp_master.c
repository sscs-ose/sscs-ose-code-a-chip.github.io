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
#include <stdlib.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_master_u.h"

/* MPP include files */
#include "mpp.h"

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
   mpp_problem *mpp = (mpp_problem *) calloc(1, sizeof(mpp_problem));
  
   *user = mpp;
   
   return(USER_SUCCESS);
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
   mpp_problem *mpp = (mpp_problem *) user;
   mpp_parameters *par = &(mpp->par);
   
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
   /* This gives you access to the user data structure. */
   mpp_problem *mpp = (mpp_problem *) user;
   mpp_parameters *par = &(mpp->par);
   char *infile = par->infile;
   FILE *f = NULL;
   char line[MAX_LINE_LENGTH], key[50], value[50];
   int numvars, i;

   /* Make sure the file exists and can be opened */
   if (!strcmp(infile, "")){
      printf("\nMpp I/O: No problem data file specified\n\n");
      exit(1);
   }
   
   if ((f = fopen(infile, "r")) == NULL){
      printf("Readparams: file %s can't be opened\n", infile);
      exit(1); /*error check for existence of parameter file*/
   }

   /* The file format is to first list the number of nodes, arcs, and edges,
      and then to specify the head, tail, and cost of each arc and edge */

   /* Read in the number of nodes */
   fgets(line, MAX_LINE_LENGTH, f);
   sscanf(line, "%s%s", key, value);
   if (strcmp(key, "NUMNODES") == 0){
      READ_INT_PAR(mpp->numnodes);
   }else{
      printf("Error in input file: Expected number of nodes\n\n");
      exit(1);
   }

   /* Read in the number of arcs */
   fgets(line, MAX_LINE_LENGTH, f);
   sscanf(line, "%s%s", key, value);
   if (strcmp(key, "NUMARCS") == 0){
      READ_INT_PAR(mpp->numarcs);
   }else{
      printf("Error in input file: Expected number of arcs\n\n");
      exit(1);
   }

   /* Read in the number of edges */
   fgets(line, MAX_LINE_LENGTH, f);
   sscanf(line, "%s%s", key, value);
   if (strcmp(key, "NUMEDGES") == 0){
      READ_INT_PAR(mpp->numedges);
   }else{
      printf("Error in input file: Expected number of edges\n\n");
      exit(1);
   }

   numvars = 2 * mpp->numedges + mpp->numarcs;
   
   /* Allocate the arrays */
   mpp->type = (char *) malloc (numvars * sizeof(char));
   mpp->cost = (int *)  malloc (numvars * sizeof(int));
   mpp->head = (int *)  malloc (numvars * sizeof(int));
   mpp->tail = (int *)  malloc (numvars * sizeof(int));

   /* Read in the arcs and their data first */
   for(i = 0; i < mpp->numarcs; i++){
      if (!fgets(line, MAX_LINE_LENGTH, f)){
	 printf("Error in input file: Expected more data\n\n");
	 exit(1);
      }
      sscanf(line, "%c %i %i %i", mpp->type + i, mpp->tail + i,
	     mpp->head + i, mpp->cost + i);
      if (strncmp(mpp->type + i, "A", 1) != 0 &&
	  strncmp(mpp->type + i, "a", 1) != 0 ){
	 printf("Error in input file: Expected an arc\n\n");
	 exit(1);
      }
   }

   /* Read in the edges and their data */
   for(i = mpp->numarcs; i < mpp->numarcs + mpp->numedges; i++){
      if (!fgets(line, MAX_LINE_LENGTH, f)){
	 printf("Error in input file: Expected more data/n/n");
	 exit(1);
      }
      /*We have two variables associated with each edge, one for each direction*/
      /* First variable */
      sscanf(line, "%c %i %i %i", mpp->type + i,
	                          mpp->tail + i,
	                          mpp->head + i,
	                          mpp->cost + i);
      /* Second variable (direction reversed) */
      sscanf(line, "%c %i %i %i", mpp->type + i + mpp->numedges,
	                          mpp->head + i + mpp->numedges,
	                          mpp->tail + i + mpp->numedges,
	                          mpp->cost + i + mpp->numedges);
      if (strncmp(mpp->type + i, "E", 1) != 0 &&
	  strncmp(mpp->type + i, "e", 1) != 0 ){
	 printf("Error in input file: Expected an edge/n/n");
	 exit(1);
      }
   }
   
   if (fgets(line, MAX_LINE_LENGTH, f)){
      printf("Ignoring extra data in input file./n/n");
   }

   fclose(f);

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
   mpp_problem *mpp = (mpp_problem *) user;
   int i;

   /* Since we don't know how to form a good set of base variables, we'll put all
      the variables in the extra set */

   /* Set the number of extra variables*/
   *extravarnum = 2 * mpp->numedges + mpp->numarcs;
 
   /* The variables are automatically put in the extra set */
   *extravars = (int *) malloc(*extravarnum * ISIZE);
   for (i = 0; i < *extravarnum; i++){
     (*extravars)[i] = i;
   }

   /* Set the number of rows in the initial formulation */
   *basecutnum = mpp->numnodes + mpp->numedges;

   /* The set of base variables will be empty */
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
   mpp_problem *mpp = (mpp_problem *) user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP)

   *user_lp = mpp;

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
   mpp_problem *mpp = (mpp_problem *) user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP) && defined (COMPILE_IN_CG)

   *user_cg = mpp;
   
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
   mpp_problem *mpp = (mpp_problem *) user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP) && defined (COMPILE_IN_CP)

   *user_cp = mpp;

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
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This is the user's chance to display the solution in whatever
 * manner desired. Change the return value to USER_NO_PP if you want to
 * display the solution yourself. A return value of USER_AND_PP will cause the
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
   /* This gives you access to the user data structure. */
   mpp_problem *mpp = (mpp_problem *) (*user);

   FREE(mpp->cost);
   FREE(mpp->head);
   FREE(mpp->tail);
   FREE(mpp->type);
   if(!mpp->par.test){
     FREE(mpp);
   }
   return(USER_SUCCESS);
}
/*===========================================================================*/

/*===========================================================================*\
 * This function is used to lift the user created cuts during warm starting *
\*===========================================================================*/

int user_ws_update_cuts (void *user, int *size, char **coef, double * rhs, 
			 char *sense, char type, int new_col_num, 
			 int change_type)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/


