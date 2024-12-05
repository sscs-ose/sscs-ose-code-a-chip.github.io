/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY MILP Solver Framework.          This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* (c) Copyright 2006-2019 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_macros.h"
#include "symphony.h"
#include "sym_master.h"

#define LENGTH 100

void mckp_parse_command_line(int argc, char **argv, char *infile,
			     int *num_items, int *num_constraints,
			     int *format, char *solve_mc, double *gamma,
			     double *utopia, double *ub);
void mckp_read_problem1(sym_environment *env, char *infile, int *num_items,
			double ***objectives, double ***constraints,
			double **capacity, int *num_objectives,
			int *num_constraints);
void mckp_read_problem2(sym_environment *env, char *infile, int *num_items,
			double ***objectives, double ***constraints,
			double **capacity, int *num_objectives,
			int *num_constraints);
void mckp_read_problem3(sym_environment *env, char *infile, int *num_items,
			double ***objectives, double ***constraints,
			double **capacity, int *num_objectives,
			int *num_constraints);

/*===========================================================================*\
 * This is main() for the MCKP application
\*===========================================================================*/

int main(int argc, char **argv)
{
   char infile[LENGTH];
   int num_items = 0, format;
   double **objectives, **constraints;
   int num_objectives = 0, num_constraints = 0;
   double *capacity;
   int i, j, k;
   int nz;
   int *matbeg, *matind;
   double *matval, *lb, *ub, gamma, utopia[2];
   char *sense, *is_int, solve_mc = TRUE;
   char output_file[50];
   FILE *f;
   double mc_ub = MAXDOUBLE;

   sym_environment *env = sym_open_environment();

   sym_version();

   sym_parse_command_line(env, argc, argv);

   mckp_parse_command_line(argc, argv, infile, &num_items, &num_constraints,
			   &format, &solve_mc, &gamma, utopia, &mc_ub);

   sym_set_int_param(env, "do_reduced_cost_fixing", FALSE);

   if (format == 1){
      mckp_read_problem1(env, infile, &num_items, &objectives, &constraints,
			 &capacity, &num_objectives, &num_constraints);
   }else if (format == 2){
      mckp_read_problem2(env, infile, &num_items, &objectives, &constraints,
			 &capacity, &num_objectives, &num_constraints);
   }else if (format == 3){
      mckp_read_problem3(env, infile, &num_items, &objectives, &constraints,
			 &capacity, &num_objectives, &num_constraints);

   }else{
      fprintf(stderr, "Invalid format!\n");
      exit(0);
   }
      
   if (num_objectives != 2){
      fprintf(stderr, "Wrong number of objectives specified!\n");
      exit(0);
   }

   nz = num_items*num_constraints;
   
   matbeg  = (int *) malloc((num_items + 1) * ISIZE);
   matind  = (int *) malloc(nz * ISIZE);
   matval  = (double *) malloc(nz * DSIZE);
   ub      = (double *) malloc(num_items * DSIZE);
   lb      = (double *) calloc(num_items, DSIZE); /* zero lower bounds */
   sense   = (char *) malloc(num_constraints * CSIZE);
   is_int  = (char *) calloc(num_items, CSIZE);

   /* Convert to column-ordered format */
   for (i = 0, k = 0; i < num_items; i++){
      matbeg[i] = k;
      for (j = 0; j < num_constraints; j++){
	 matind[k] = j;
	 matval[k++] = constraints[j][i];
      }
      ub[i] = 1.0;
      is_int[i] = TRUE;
   }
   matbeg[i] = k;
   
   for (j = 0; j < num_constraints; j++){
      sense[j] = 'L';
   }
   
   sym_explicit_load_problem(env, num_items, num_constraints, matbeg, matind,
			     matval, lb, ub, is_int, objectives[0],
			     objectives[1], sense, capacity, NULL, TRUE);

   if (solve_mc){
      sym_mc_solve(env);
   }else{
      double tau = 0.0;
      sym_set_int_param(env, "multi_criteria", TRUE);
      if (gamma == 1.0){
	 tau = -1.0;
	 env->utopia[0] = 0;
	 env->utopia[1] = -MAXINT;
      }else if (gamma == 0.0){
	 gamma = -1.0;
	 tau = 1.0;
	 env->utopia[0] = -MAXINT;
	 env->utopia[1] = 0;
      }else{
	 tau = 1 - gamma;
	 env->utopia[0] = utopia[0];
	 env->utopia[1] = utopia[1];
      }
      sym_set_dbl_param(env, "mc_gamma", gamma);
      sym_set_dbl_param(env, "mc_tau", tau);
      sym_set_int_param(env, "mc_find_supported_solutions", FALSE);
      memcpy((char *)env->mip->obj1, (char *)env->mip->obj, DSIZE*env->mip->n);
      if (mc_ub < MAXDOUBLE){
	 env->ub = env->mc_ub = mc_ub;
	 env->has_mc_ub = env->has_ub = TRUE;
      }
      env->obj[0] = env->obj[1] = 0.0;
      env->base->cutnum += 2;
      env->rootdesc->uind.size++;
      env->rootdesc->uind.list = (int *) realloc(env->rootdesc->uind.list,
					 env->rootdesc->uind.size*ISIZE);
      env->rootdesc->uind.list[env->rootdesc->uind.size-1] = env->mip->n;
      env->par.tm_par.granularity = env->par.lp_par.granularity =
	 -MAX(env->par.lp_par.mc_rho, env->par.mc_compare_solution_tolerance);
      sym_solve(env);
      sprintf(output_file, "output.%s", argv[6]);
      if (!(f = fopen(output_file, "w"))){
	 printf("\nError opening output file\n\n");
      }else{
	 fprintf(f, "Gamma: %.10f\n", gamma);
	 if (env->obj[0] == 0.0 && env->obj[1] == 0.0){
	    fprintf(f, "Subproblem Infeasible\n");
	 }else{
	    fprintf(f, "First Objective: %lf\n", env->obj[0]);
	    fprintf(f, "Second Objective: %lf\n", env->obj[1]);
	 }
      }
      fclose(f);
   }

   sym_close_environment(env);

   for (i = 0; i < num_objectives; i++){
      free(objectives[i]);
   }
   free(objectives);

   for (i = 0; i < num_constraints; i++){
      free(constraints[i]);
   }
   free(constraints);
   free(capacity);

   free(matbeg);
   free(matind);
   free(matval);
   free(ub);
   free(lb);
   free(sense);
   free(is_int);
   
   return(0);
}

/*===========================================================================*\
 * This is the function that reads the command line
\*===========================================================================*/

void mckp_parse_command_line(int argc, char **argv, char *infile,
			     int *num_items, int *num_constraints,
			     int *format, char *solve_mc, double *gamma,
			     double *utopia, double *ub)
{
   int i, tmpi;
   char foundF = FALSE, foundT = FALSE;
   char tmp, c;
   char line[LENGTH];
   double tmpd;

   for (i = 1; i < argc; i++){
      sscanf(argv[i], "%c %c", &tmp, &c);
      if (tmp != '-')
	 continue;
      switch (c) {
       case 'F':
	 if (i < argc - 1){
	    sscanf(argv[i+1], "%c", &tmp); 
	    if (tmp == '-'){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       strncpy(infile, argv[++i], LENGTH);
	       foundF = TRUE;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;	     
       case 'U':
	 if (i < argc - 1){
	    sscanf(argv[i+1], "%lf", &tmpd); 
	    if (tmp == '-'){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       *ub = tmpd;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;	     
       case 'N':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%d", &tmpi)){ 
	       printf("Warning: Missing argument to command-line switch -%c",
		      c);
	       printf("\n");
	    }else{
	       i++;
	       *num_items = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;	     
       case 'C':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%d", &tmpi)){ 
		printf("Warning: Missing argument to command-line switch -%c",
		       c);
		printf("\n");
	    }else{
	       i++;
	       *num_constraints = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;	     
       case 'T':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%d", &tmpi)){
		printf("Warning: Missing argument to command-line switch -%c",
		       c);
		printf("\n");
	    }else{
	       i++;
	       *format = tmpi;
	       foundT = TRUE;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;	     
       case 'G':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%lf", &tmpd)){ 
		printf("Warning: Missing argument to command-line switch -%c",
		       c);
		printf("\n");
	    }else{
	       i++;
	       *gamma = tmpd;
	       *solve_mc = FALSE;
	       if (tmpd != 1.0 && tmpd != 0.0){
		  if (!sscanf(argv[i+1], "%lf", &tmpd)){ 
		     printf("Warning: Missing argument to command-line switch -%c",
			    c);
		     printf("\n");
		  }else{
		     i++;
		     utopia[0] = tmpd;
		  }
		  if (!sscanf(argv[i+1], "%lf", &tmpd)){ 
		     printf("Warning: Missing argument to command-line switch -%c",
			    c);
		     printf("\n");
		  }else{
		     i++;
		     utopia[1] = tmpd;
		  }
	       }
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;	     
      default:
	 break;
      }	 
   }
   
   if (!foundF){
      fprintf(stderr, "MCKP I/O: file name not specified\n", infile);
      exit(1);
   }
   if (!foundT){
      fprintf(stderr, "MCKP I/O: file format not specified\n", infile);
      exit(1);
   }
}

/*===========================================================================*\
 * This is the function that reads in the data file in format 1
\*===========================================================================*/

void mckp_read_problem1(sym_environment *env, char *infile, int *num_items,
			double ***objectives, double ***constraints,
			double **capacity, int *num_objectives,
			int *num_constraints)
{
   char line[LENGTH], line1[LENGTH];
   FILE *f;
   double **obj, **cons;
   double *cap;
   int num_obj = 0, num_cons = 0, count = 0;
   char key[LENGTH];
   int max_num_items = *num_items;
   int max_num_cons = *num_constraints;
      
   if (!max_num_items){
      fprintf(stderr, "MCKP I/O: format 1 requires number of items to be\n");
      fprintf(stderr, "specified.\n");
      exit(0);
   }

   if ((f = fopen(infile, "r")) == NULL){
      fprintf(stderr, "MCKP I/O: file '%s' can't be opened\n", infile);
      exit(1);
   }
   
   if (!max_num_cons){
      max_num_cons = 10;
   }
   
   obj = *objectives = (double **) calloc(2, sizeof(double *));
   cons = *constraints = (double **) calloc(max_num_cons, sizeof(double *));
   cap = *capacity = (double *) calloc(max_num_cons, sizeof(double));
   
   obj[0] = (double *) calloc(max_num_items, sizeof(double));
   obj[1] = (double *) calloc(max_num_items, sizeof(double));
   
   while (NULL != fgets(line, LENGTH, f)){
      strcpy(key, "");
      sscanf(line,"%s", key); /*read in next keyword*/
      if (strcmp("=", key) == 0){
	 if (NULL != fgets(line, LENGTH, f)){
	    strcpy(key,"");
	    sscanf(line,"%s",key); /*read in next keyword*/
	    if (strcmp("knapsack", key) == 0){
	       if (NULL != fgets(line, LENGTH, f)){
		  strcpy(key,"");
		  sscanf(line,"%s",key); /*read in next keyword*/
		  if (strcmp("capacity:", key) == 0){
		     if (strchr(line,':')){
			strcpy(line1, strchr(line, ':')+1);
		     }
		     sscanf(line1, "%lf", (*capacity) + num_cons); 
		  }else{
		     fprintf(stderr, "MCKP I/O: Unexpected keyword in",
			     "input file!\n");
		     exit(1);
		  }
		  count = 0;
		  cons[num_cons] = (double *) calloc(max_num_items,
						     sizeof(double));
		  while (NULL != fgets(line, LENGTH, f)){
		     strcpy(key,"");
		     sscanf(line,"%s",key); /*read in next keyword*/
		     if (strcmp("item", key) != 0){
			fprintf(stderr, "MCKP I/O: Unexpected keyword in",
				"input file!\n");
			exit(1);
		     }
		     if (NULL != fgets(line, LENGTH, f)){
			strcpy(key,"");
			sscanf(line,"%s",key); /*read in next keyword*/
			if (strcmp("weight:", key) == 0){
			   if (num_cons < max_num_cons){
			      if (strchr(line,':')){
				 strcpy(line1, strchr(line, ':')+1);
			      }
			      sscanf(line1, "%lf", (cons[num_cons]) + count);
			   }
			}else{
			   fprintf(stderr, "MCKP I/O: Unexpected keyword in",
				   "input file!\n");
			   exit(1);
			}
		     }else{
			fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
			exit(1);
		     }
		     if (NULL != fgets(line, LENGTH, f)){
			strcpy(key,"");
			sscanf(line,"%s",key); /*read in next keyword*/
			if (strcmp("profit:", key) == 0){
			   if (num_obj < 2){
			      if (strchr(line,':')){
				 strcpy(line1, strchr(line, ':')+1);
			      }
			      sscanf(line1, "%lf", (obj[num_obj]) + count);
			      obj[num_obj][count] *= -1;
			   }
			}else{
			   fprintf(stderr, "MCKP I/O: Unexpected keyword in",
				   "input file!\n");
			   exit(1);
			}
		     }else{
			fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
			exit(1);
		     }
		     if (++count == max_num_items){
			break;
		     }
		  }
		  if (count != max_num_items){
		     fprintf(stderr, "MCKP I/O: Not enough items!\n");
		     exit(1);
		  }
		  num_obj++;
		  num_cons++;
	       }else{
		  fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
		  exit(1);
	       }
	    }else{
	       fprintf(stderr,"MCKP I/O: Unexpected keyword in input file!\n");
	       exit(1);
	    }
	 }else{
	    fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
	    exit(1);
	 }
      }     
   }

   *num_objectives = num_obj > 2 ? 2 : num_obj;
   *num_constraints = num_cons > max_num_cons ? max_num_cons : num_cons;

   fclose(f);
}   

/*===========================================================================*\
 * This is the function that reads in the data file in format 2
\*===========================================================================*/

void mckp_read_problem2(sym_environment *env, char *infile, int *num_items,
			double ***objectives, double ***constraints,
			double **capacity, int *num_objectives,
			int *num_constraints)
{
   char line[LENGTH], line1[LENGTH];
   FILE *f;
   double **obj, **cons;
   double *cap;
   int num_obj = 0, num_cons = 0;
   char key[LENGTH];
   int i;
   int max_num_items = *num_items;
   int max_num_cons = *num_constraints;
   
   if ((f = fopen(infile, "r")) == NULL){
      fprintf(stderr, "MCKP I/O: file '%s' can't be opened\n", infile);
      exit(1);
   }

   obj = *objectives = (double **) calloc(2, sizeof(double *));

   while (NULL != fgets(line, LENGTH, f)){
      strcpy(key, "");
      sscanf(line,"%s", key); /*read in next keyword*/
      if (strcmp("#", key) == 0){
	 switch (line[2]){
	  case 'N':
	    if (NULL != fgets(line, LENGTH, f)){
	       sscanf(line, "%i", num_items);
	       if (max_num_items){
		  max_num_items = *num_items > max_num_items ?
		     max_num_items : *num_items;
		  *num_items = max_num_items;
	       }else{
		  max_num_items = *num_items;
	       }
	    }else{
	       fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
	       exit(1);
	    }
	    obj[0] = (double *) calloc(max_num_items, sizeof(double));
	    obj[1] = (double *) calloc(max_num_items, sizeof(double));
	    break;
	    
	  case 'P':
	    break;
	    
	  case 'K':
	    if (NULL != fgets(line, LENGTH, f)){
	       sscanf(line, "%i", num_constraints);
	       if (max_num_cons){
		  max_num_cons = *num_constraints > max_num_cons ?
		     max_num_cons : *num_constraints;
		  *num_constraints = max_num_cons;
	       }else{
		  max_num_cons = *num_constraints;
	       }
	    }else{
	       fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
	       exit(1);
	    }
	    cons = *constraints = (double **) calloc(*num_constraints,
						     sizeof(double *));
	    cap = *capacity = (double *) calloc(*num_constraints,
						sizeof(double));
	    break;

	  case 'O':
	    if (num_obj <2){
	       for (i = 0; i < max_num_items;){
		  if (NULL != fgets(line, LENGTH, f)){
		     if (strcmp("\r\n", line) != 0){
			sscanf(line, "%lf", obj[num_obj] + i);
			obj[num_obj][i] *= -1;
			i++;
		     }
		  }else{
		     fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
		     exit(1);
		  }
	       }
	       num_obj++;
	    }
	    break;

	  case 'C':
	    if (num_cons < max_num_cons){
	       cons[num_cons] = (double *) calloc(max_num_items,
						  sizeof(double));
	       for (i = 0; i < max_num_items;){
		  if (NULL != fgets(line, LENGTH, f)){
		     if (strcmp("\r\n", line) != 0){
			sscanf(line, "%lf", cons[num_cons] + i);
			i++;
		     }
		  }else{
		     fprintf(stderr, "MCKP I/O: Unexpected end of file!\n");
		     exit(1);
		  }
	       }
	       while (NULL != fgets(line, LENGTH, f)){
		  if (strcmp("\r\n", line) != 0){
		     sscanf(line, "%lf", (*capacity) + num_cons);
		     break;
		  }
	       }
	    }
	    num_cons++;
	    break;

	  default:
	    break;

	 }
      }
   }

   *num_objectives = num_obj;
   *num_constraints = num_cons;

   fclose(f);
}

/*===========================================================================*\
 * This is the function that reads in the data file in format 3
\*===========================================================================*/

void mckp_read_problem3(sym_environment *env, char *infile, int *num_items,
			double ***objectives, double ***constraints,
			double **capacity, int *num_objectives,
			int *num_constraints)
{
   char line[LENGTH], line1[LENGTH];
   FILE *f;
   double **obj, **cons;
   double *cap;
   int num_obj = 0, count = 0;
   char key[LENGTH];
   int i;
   int max_num_items = *num_items;
   
   *num_constraints = 1;
   *num_objectives = 2;
   
   if ((f = fopen(infile, "r")) == NULL){
      fprintf(stderr, "MCKP I/O: file '%s' can't be opened\n", infile);
      exit(1);
   }

   obj = *objectives = (double **) calloc(2, sizeof(double *));
   cons = *constraints = (double **) calloc(1, sizeof(double *));
   *capacity = (double *) calloc(1, sizeof(double));
   
   while (NULL != fgets(line, LENGTH, f)){
      switch (line[0]){
       case 'c':
	 break;

       case 'n':
	 sscanf(line+1, "%i", num_items);
	 if (max_num_items){
	    max_num_items = *num_items > max_num_items ?
	       max_num_items : *num_items;
	    *num_items = max_num_items;
	 }else{
	    max_num_items = *num_items;
	 }
	 obj[0] = (double *) calloc(max_num_items, sizeof(double));
	 obj[1] = (double *) calloc(max_num_items, sizeof(double));
	 cons[0] = (double *) calloc(max_num_items, sizeof(double));
	 break;	    
   
       case 'i':
	 if (count < max_num_items){
	    sscanf(line+1, "%lf %lf %lf", cons[0] + count, obj[0] + count,
		   obj[1] + count);
	    obj[0][count] *= -1;
	    obj[1][count] *= -1;
	    count++;
	 }
	 break;

       case 'W':
	 sscanf(line+1, "%lf", *capacity);
      }
   }
	    
   fclose(f);
}
