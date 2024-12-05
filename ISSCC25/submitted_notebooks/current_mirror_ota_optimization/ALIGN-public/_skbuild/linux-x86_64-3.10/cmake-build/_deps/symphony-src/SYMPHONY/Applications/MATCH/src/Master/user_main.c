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

#include "symphony.h"
#include "sym_master.h"
#include "user.h"

#include <stdlib.h>


int match_test(sym_environment *env);

int main(int argc, char **argv)
{

   int termcode;
   char * infile;

   /* Create a SYMPHONY environment */
   sym_environment *env = sym_open_environment();

   /* Print version info */
   sym_version();
   
   /* Create the data structure for storing the problem instance.*/
   user_problem *prob = (user_problem *)calloc(1, sizeof(user_problem));
   
   CALL_FUNCTION( sym_set_user_data(env, (void *)prob) );

   CALL_FUNCTION( sym_parse_command_line(env, argc, argv) );

   if(prob->par.test){

      match_test (env);

   } else {
    
     CALL_FUNCTION( match_read_data(prob, prob->par.infile) );
     
     CALL_FUNCTION( match_load_problem(env, prob) );

# if 0
     int colsNum=-1;
     sym_get_num_cols(env, &colsNum);
     for(int j=0; j<=colsNum; ++j) {
       int isInt=666;
       int code=sym_is_integer(env, j, &isInt);
       printf("j=%d  code=%d  isInt=%d\n", j, code, isInt);
     }  // j
#endif

     CALL_FUNCTION( sym_solve(env) );
   }
     
   CALL_FUNCTION( sym_close_environment(env) );
   
   return(0);
   
}

/*===========================================================================*\
\*===========================================================================*/

int match_read_data(user_problem *prob, char *infile)
{
   int i, j;
   FILE *f = NULL;

   if ((f = fopen(infile, "r")) == NULL){
      printf("main(): user file %s can't be opened\n", infile);
      return(ERROR__USER); 
   }

   /* Read in the costs */
   fscanf(f,"%d",&(prob->numnodes));
   for (i = 0; i < prob->numnodes; i++)
      for (j = 0; j < prob->numnodes; j++)
	 fscanf(f, "%d", &(prob->cost[i][j]));
   
   return (FUNCTION_TERMINATED_NORMALLY);
}

/*===========================================================================*\
\*===========================================================================*/

int match_load_problem(sym_environment *env, user_problem *prob){
   
   int i, j, index, n, m, nz, *column_starts, *matrix_indices;
   double *matrix_values, *lb, *ub, *obj, *rhs, *rngval;
   char *sense, *is_int;
   
   /* set up the inital LP data */
   n = prob->numnodes*(prob->numnodes-1)/2;
   m = prob->numnodes;
   nz = 2 * n;

   /* Allocate the arrays */
   column_starts  = (int *) malloc((n + 1) * ISIZE);
   matrix_indices = (int *) malloc((nz) * ISIZE);
   matrix_values  = (double *) malloc((nz) * DSIZE);
   obj            = (double *) malloc(n * DSIZE);
   lb             = (double *) calloc(n, DSIZE);
   ub             = (double *) malloc(n * DSIZE);
   rhs            = (double *) malloc(m * DSIZE);
   sense          = (char *) malloc(m * CSIZE);
   rngval         = (double *) calloc(m, DSIZE);
   is_int         = (char *) malloc(n * CSIZE);
   
   /* Fill out the appropriate data structures -- each column has
      exactly two entries */
   index = 0;
   for (i = 0; i < prob->numnodes; i++) {
      for (j = i+1; j < prob->numnodes; j++) {
	 prob->match1[index] = i; /*The first component of assignment 'index'*/
	 prob->match2[index] = j; /*The second componet of assignment 'index'*/
	 /* So we can recover the index later */
	 prob->index[i][j] = prob->index[j][i] = index;
	 obj[index] = prob->cost[i][j]; /* Cost of assignment (i, j) */
	 is_int[index] = TRUE;
	 column_starts[index] = 2*index;
	 matrix_values[2*index] = 1;
	 matrix_values[2*index+1] = 1;
	 matrix_indices[2*index] = i;
	 matrix_indices[2*index+1] = j;
	 ub[index] = 1.0;
	 index++;
      }
   }
   column_starts[n] = 2 * n;
   
   /* set the initial right hand side */
   for (i = 0; i < m; i++) {
      rhs[i] = 1;
      sense[i] = 'E';
   }
   
   /* Load the problem to SYMPHONY */   
   sym_explicit_load_problem(env, n, m, column_starts, matrix_indices,
			     matrix_values, lb, ub, is_int, obj, 0, sense, rhs,
			     rngval, true);
			     
   FREE(column_starts);
   FREE(matrix_indices);
   FREE(matrix_values);
   FREE(lb);
   FREE(ub);
   FREE(obj);
   FREE(sense);
   FREE(rhs);
   FREE(rngval);
   FREE(is_int);

   return (FUNCTION_TERMINATED_NORMALLY);

}

/*===========================================================================*\
\*===========================================================================*/

int match_test(sym_environment *env)
{

   int termcode, i, file_num = 1;
   char input_files[1][MAX_FILE_NAME_LENGTH +1] = {"sample.mat"};
   
   double sol[1] = {5.00};
   
   char *input_dir = (char*)malloc(CSIZE*(MAX_FILE_NAME_LENGTH+1));
   char *infile = (char*)malloc(CSIZE*(MAX_FILE_NAME_LENGTH+1));
   double *obj_val = (double *)calloc(DSIZE,file_num);
   double tol = 1e-03;
   user_problem *prob = (user_problem *) env->user;
  
   if (strcmp(env->par.test_dir, "") == 0){ 
     strcpy(input_dir, ".");
   } else{
     strcpy(input_dir, env->par.test_dir);
   }
  
   sym_set_int_param(env, "verbosity", -10);

  for(i = 0; i<file_num; i++){

    strcpy(infile, "");
    sprintf(infile, "%s%s%s", input_dir, "/", input_files[i]);
   
    CALL_FUNCTION( match_read_data(prob, infile) );
    
    CALL_FUNCTION( match_load_problem(env, prob) );

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

  FREE(input_dir);
  FREE(infile);
  FREE(obj_val);
  
  return(0);

}

