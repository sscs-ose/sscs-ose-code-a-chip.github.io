/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* The author of this file is Menal Guzelsoy                                 */
/*                                                                           */
/* (c) Copyright 2005-2019 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/*-------------------------------------------------------------------------*/
/*
  This is an example of using SYMPHONY to construct and solve 
  a simple MILP.

  optimal solution: x* = (1,1)
  
  minimize -1 x0 - 1 x1
  s.t       1 x0 + 2 x1 <= 3
            2 x0 + 1 x1 <= 3
              x0        >= 0 integer
              x1        >= 0 integer
*/

/*-------------------------------------------------------------------------*/

#include "symphony.h"
#include <iostream>
#include <malloc.h>

int main(int argc, char* argv[]){

   /* Create a SYMPHONY environment */
   
   sym_environment *env = sym_open_environment();

   int n_cols = 2; //number of columns
   double * objective    = 
      (double *) malloc(sizeof(double) * n_cols);//the objective coefficients
   double * col_lb       = 
      (double *) malloc(sizeof(double) * n_cols);//the column lower bounds
   double * col_ub       = 
      (double *) malloc(sizeof(double) * n_cols);//the column upper bounds
    
   //Define the objective coefficients.
   //minimize -1 x0 - 1 x1
   objective[0] = -1.0;
   objective[1] = -1.0;
   
   //Define the variable lower/upper bounds.
   // x0 >= 0   =>  0 <= x0 <= infinity
   // x1 >= 0   =>  0 <= x1 <= infinity
   col_lb[0] = 0.0;
   col_lb[1] = 0.0;
   col_ub[0] = sym_get_infinity();
   col_ub[1] = sym_get_infinity();
   
   int n_rows = 2;
   char * row_sense = 
      (char *) malloc (sizeof(char) * n_rows); //the row senses
   double * row_rhs = 
      (double *) malloc (sizeof(double) * n_rows); //the row right-hand-sides
   double * row_range = NULL; //the row ranges   
   row_sense[0] = 'L';
   row_rhs[0] = 3;
   row_sense[1] = 'L';
   row_rhs[1] = 3;

   /* Constraint matrix definitions */
   int non_zeros = 4;
   int * start = (int *) malloc (sizeof(int) * (n_cols + 1)); 
   int * index = (int *) malloc (sizeof(int) * non_zeros);
   double * value = (double *) malloc (sizeof(double) *non_zeros);

   start[0] = 0; 
   start[1] = 2;
   start[2] = 4;

   index[0] = 0;
   index[1] = 1;
   index[2] = 0;
   index[3] = 1;

   value[0] = 1;
   value[1] = 2;
   value[2] = 2;
   value[3] = 1;

   //define the integer variables

   char * int_vars = (char *) malloc (sizeof(char) * n_cols);

   int_vars[0] = TRUE;
   int_vars[1] = TRUE;

   //load the problem to environment
   sym_explicit_load_problem(env, n_cols, n_rows, start, index, value, col_lb, 
			     col_ub, int_vars, objective, NULL, row_sense, 
			     row_rhs, row_range, TRUE);

    //solve the integer program
   sym_solve(env);
   
   //get, print the solution
   double * solution = (double *) malloc (sizeof(double) * n_cols);
   double objective_value = 0.0;

   sym_get_col_solution(env, solution);
   sym_get_obj_val(env, &objective_value);

   printf("%s\n%s%f\n%s%f\n%s%f\n","The optimal solution is",
	  " x0 = ",solution[0],
	  " x1 = ",solution[1],
	  " with objective value = ",objective_value);
   
   //free the memory
   sym_close_environment(env);

   if(objective){free(objective);}
   if(col_lb)   {free(col_lb);}
   if(col_ub)   {free(col_ub);}
   if(row_rhs)  {free(row_rhs);}
   if(row_sense){free(row_sense);}
   if(row_range){free(row_range);}
   if(index)    {free(index);}
   if(start)    {free(start);}
   if(value)    {free(value);}
   if(int_vars) {free(int_vars);}
   if(solution) {free(solution);}
   return 0;

}

