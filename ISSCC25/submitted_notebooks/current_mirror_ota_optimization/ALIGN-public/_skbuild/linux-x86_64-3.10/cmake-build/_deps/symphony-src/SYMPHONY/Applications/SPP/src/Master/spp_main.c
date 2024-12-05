/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY Branch, Cut, and Price Library.         */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* (c) Copyright 2000-2005-2007 Ted Ralphs. All Rights Reserved.             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/
/*===========================================================================*/

#define CALL_FUNCTION(f) \
if ((termcode = f) < 0){                                                    \
   printf("Error detected: termcode = %i\n", termcode);                     \
   printf("Exiting...\n\n");                                                \
   exit(termcode);                                                          \
}

/*===========================================================================*\
   This file contains the main() for the master process.

   Note that, if you want to use the OSI SYMPHONY interface, you should set the
   USE_OSI_INTERFACE flag and define the COINROOT path in the SYMPHONY 
   Makefile. Otherwise, the C callable library functions will be used by 
   default. See below for the usage.
\*===========================================================================*/

#if defined(USE_OSI_INTERFACE)

#include "OsiSymSolverInterface.hpp"

int main(int argc, char **argv)
{
   OsiSymSolverInterface si;

   /* Parse the command line */
   si.parseCommandLine(argc, argv);
   
   /* Read in the problem */
   si.loadProblem();

   /* Find a priori problem bounds */
   si.findInitialBounds();

   /* Solve the problem */
   si.branchAndBound();
   
   return(0);
}

#else

#include "symphony.h"
#include "sym_master.h"
#include "spp.h"
#include <stdlib.h>

int spp_test(sym_environment *env);

int main(int argc, char **argv)
{

   int termcode;
   spp_problem *spp;

   sym_environment *env = sym_open_environment();

   sym_version();
      
   CALL_FUNCTION( sym_parse_command_line(env, argc, argv) );

   CALL_FUNCTION( sym_get_user_data(env, (void **)&spp) );

   if(spp->par->test){

     spp_test(env);

   } else {

     CALL_FUNCTION( sym_load_problem(env) );
     
     CALL_FUNCTION( sym_find_initial_bounds(env) );
     
     CALL_FUNCTION( sym_solve(env) );
     
   }

   CALL_FUNCTION( sym_close_environment(env) );

   return(0);
}

/*===========================================================================*\
\*===========================================================================*/

int spp_test(sym_environment *env) 
{
    int termcode, i, file_num = 2;
   char input_files[1][MAX_FILE_NAME_LENGTH +1] = {"sample.spp"};
   
   double sol[1] = {6314.00};
   
   char *input_dir = (char*)malloc(CSIZE*(MAX_FILE_NAME_LENGTH+1));
   char *infile = (char*)malloc(CSIZE*(MAX_FILE_NAME_LENGTH+1));
   double *obj_val = (double *)calloc(DSIZE,file_num);
   double tol = 1e-06;
   spp_problem *spp;

   CALL_FUNCTION( sym_get_user_data(env, (void **)&spp) );

   if (strcmp(spp->par->test_dir, "") == 0){ 
     strcpy(input_dir, ".");
   } else{
     strcpy(input_dir, spp->par->test_dir);
   }
  
   sym_set_int_param(env, "verbosity", -10);
   spp->par->verbosity = -10;

  for(i = 0; i<file_num; i++){

    strcpy(infile, "");
    sprintf(infile, "%s%s%s", input_dir, "/", input_files[i]);
    strcpy(spp->par->infile, infile);

    CALL_FUNCTION( sym_load_problem(env) );

    printf("Solving %s...\n", input_files[i]); 

    CALL_FUNCTION( sym_solve(env) );

    sym_get_obj_val(env, &obj_val[i]);

    if((obj_val[i] < sol[i] + tol) && 
       (obj_val[i] > sol[i] - tol)){
      printf("Success!\n");
    } else {
      printf("Failure!(%f, %f) \n", obj_val[i], sol[i]);
    }

    if(env->mip->n && i + 1 < file_num){
      free_master_u(env);
      strcpy(env->par.infile, "");
      env->mip = (MIPdesc *) calloc(1, sizeof(MIPdesc));
    }
  }

  spp->par->test = FALSE;

  FREE(input_dir);
  FREE(infile);
  FREE(obj_val);
  
  return(0); 

}

#endif

