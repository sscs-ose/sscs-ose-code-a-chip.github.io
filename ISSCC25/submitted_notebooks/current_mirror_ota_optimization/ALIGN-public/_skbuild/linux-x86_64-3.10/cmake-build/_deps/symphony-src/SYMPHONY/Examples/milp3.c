/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* The author of this file is Menal Guzelsoy                                 */
/*                                                                           */
/* (c) Copyright 2005-2014 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* This is an example of printing out all solutions in the pool after solving*/

#include "symphony.h"

#include <stdlib.h>
#include <stdio.h>
  
int main(int argc, char **argv)
{    
   int num_solutions, num_cols, i;
   double *sol, objval;
   
   sym_environment *env = sym_open_environment();
   
   sym_parse_command_line(env, argc, argv);
   
   sym_load_problem(env);

   sym_solve(env);

   sym_get_num_cols(env, &num_cols);
   sym_get_sp_size(env, &num_solutions);
   sol = (double *) malloc(num_cols*sizeof(double));
   for (i = 0; i < num_solutions; i++){
      sym_get_sp_solution(env, i, sol, &objval);
      printf("Solution of value %f found\n", objval);
   }
   free(sol);

   sym_close_environment(env);
   
   return(0);
}  
