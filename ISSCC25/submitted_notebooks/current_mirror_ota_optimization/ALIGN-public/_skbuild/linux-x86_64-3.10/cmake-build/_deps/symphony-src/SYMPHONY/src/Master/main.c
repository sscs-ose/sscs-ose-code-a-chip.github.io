/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* (c) Copyright 2000-2019 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/*===========================================================================*\
 * This file contains the main() for the SYMPHONY generic MIP solver.
 * Note that, if you want to use the OSI SYMPHONY interface, you should set the
 * USE_OSI_INTERFACE flag and define the COINROOT path in the SYMPHONY 
 * Makefile. Otherwise, the C callable library functions will be used by 
 * default. See below for the usage.
\*===========================================================================*/

#ifdef _OPENMP
#include "omp.h"
#endif

#ifdef USE_OSI_INTERFACE

#include "OsiSymSolverInterface.hpp"

int main(int argc, char **argv)
{

   /* Create an OsiSym object */
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
#include "sym_messages.h"
#if defined HAS_READLINE
#include <pwd.h>
#include <readline/readline.h>
#include <readline/history.h>

#if (RL_VERSION_MAJOR == 5 && RL_VERSION_MINOR >= 2) || \
   (RL_VERSION_MAJOR >= 6)

typedef struct {
  char *name;			
} COMMAND;

COMMAND main_commands[] = {
  { "load" },
  { "solve" },
  { "lpsolve" },
  { "set" },
  { "display" },
  { "reset" },
  { "help" },
  { "quit" },
  { "exit" },
  { (char *)NULL}
};

COMMAND display_commands[] = {
  { "solution" },
  { "obj" },
  { "stats" },
  { "parameter" },
  { "back" },
  { "quit" },
  { "exit" },
  { (char *)NULL}
};


COMMAND parameter_commands[] = {
  { "verbosity" },
  { "upper_bound" },
  { "find_first_feasible" },
  { "generate_cgl_cuts" },
  { "generate_cgl_gomory_cuts" },
  { "generate_cgl_redsplit_cuts" },
  { "generate_cgl_knapsack_cuts" },
  { "generate_cgl_oddhole_cuts" },
  { "generate_cgl_probing_cuts" },
  { "generate_cgl_clique_cuts" },
  { "generate_cgl_mir_cuts" },
  { "generate_cgl_twomir_cuts" },
  { "generate_cgl_flow_and_cover_cuts" },
  { "generate_cgl_rounding_cuts" },
  { "generate_cgl_lift_and_project_cuts" },
  { "generate_cgl_landp_cuts" },
  { "node_selection_rule" },
  { "strong_branching_candidate_num" },
  { "compare_candidadates_dafult" },
  { "select_child_default" },
  { "diving_threshold" },
  { "diving_strategy" },
  { "do_reduced_cost_fixing" },
  { "time_limit" },
  { "node_limit" },
  { "gap_limit" },
  { "param_file" },
  { "do_primal_heuristic" },
  { "should_use_rel_br" },
  { "prep_level" },
  { "tighten_root_bounds" },
  { "limit_strong_branching_time" },
  { "back" },
  { "quit" },
  { "exit" },
  { (char *)NULL}
};

char **sym_completion(const char *text, int start, int end);   
void sym_initialize_readline();
char *command_generator (const char *text, int state);
char *alloc_str (char *s);
void sym_read_tilde(char input[]);

#endif
#endif

int comp_level = 0;
int main_level = 0; /* 0 - SYMPHONY:
		       1 - SYMPHONY\Display:
		       2 - SYMPHONY\Set:
		       3 - SYMPHONY\Display\Parameter:
		    */

int sym_help(const char *line);
int sym_read_line(const char *prompt, char **input);
int sym_free_env(sym_environment *env);

int main(int argc, char **argv)
{    

   sym_environment *env = sym_open_environment();
   int termcode;
   
   if (argc > 1){
   
      sym_parse_command_line(env, argc, argv);

      if (env->par.verbosity >= 0){
	 sym_version();
      }
      
      if (env->par.test){

	 sym_test(env, argc, argv, &termcode);
	 
      }else{
	 
	 if ((termcode = sym_load_problem(env)) < 0){
	    printf("\nFatal errors encountered. Exiting with code %i.\n",
		   termcode);
	    printf("See symphony.h for meaning of code.\n\n");
	    exit(termcode);
	 }
	 
	 if ((termcode = sym_find_initial_bounds(env)) < 0){
	    printf("\nFatal errors encountered. Exiting with code %i.\n",
		   termcode);
	    printf("See symphony.h for meaning of code.\n\n");
	    exit(termcode);
	 }
	 printf("\n");
	 if (env->mip->obj2 != NULL){
	    sym_mc_solve(env);
	 } else {
	    sym_solve(env);
	 }
      }
   
   } else{

     FILE *f = NULL;
     char *line = NULL;
     char args[3][MAX_LINE_LENGTH + 1];
     char param[MAX_LINE_LENGTH +1], value[MAX_LINE_LENGTH+1];
     char ext[5];     
     int last_dot = 0, j, terminate = FALSE, termcode = 0, int_value = 0;
     int last_level = 0;
     char * is_int = NULL;
     double objval = 0.0, initial_time = 0.0, start_time = 0.0;
     double finish_time = 0.0, dbl_value = 0;

     sym_version();
     printf("***** WELCOME TO SYMPHONY INTERACTIVE MIP SOLVER ******\n\n"
	    "Please type 'help'/'?' to see the main commands!\n\n");

     sym_set_int_param(env, "verbosity", -1);

#if defined(HAS_READLINE) && ((RL_VERSION_MAJOR == 5 && \
			       RL_VERSION_MINOR >= 2) || \
 			      (RL_VERSION_MAJOR >= 6))
     sym_initialize_readline();
#endif
     
     while(true){
       main_level = last_level = 0;
       for(j = 0; j< 3; j++)
	  strcpy(args[j], "");
       sym_read_line("SYMPHONY: ", &line);
       sscanf(line, "%s%s%s", args[0], args[1], args[2]); 
       
       if (strcmp(args[0], "help") == 0 || strcmp(args[0], "?") == 0) {
	 if ((strcmp(args[1], "set") == 0)){
	   sym_help("set_help");
	 } else if ((strcmp(args[1], "display") == 0)){
	   sym_help("display_help");
	 } else  sym_help("main_help");
       } else if (strcmp(args[0], "load") == 0){ 

	 if(strcmp(args[1], "") == 0){
	   sym_read_line("Name of the file: ", &line);
	   strcpy(args[1], line);
	 }	 

#if defined(HAS_READLINE) && ((RL_VERSION_MAJOR == 5 && \
			       RL_VERSION_MINOR >= 2) || \
			      (RL_VERSION_MAJOR >= 6))
	 sym_read_tilde(args[1]);	 
#endif	 	 
	 if (fopen(args[1], "r") == NULL){
	   printf("Input file '%s' can't be opened\n",
		  args[1]);
	   continue;
	 }

	 /* check to see if SYMPHONY knows the input type! */

	 last_dot = 0;
	 for (j = 0;; j++){
	   if (args[1][j] == '\0')
	     break;
	   if (args[1][j] == '.') {
	     last_dot = j;
	   }
	 } 
	 if(last_dot){
	    strcpy(ext, args[1] + last_dot + 1);
	 }else{
	    strcpy(ext, ""); 
	 }

	 if(!(strcmp(ext, "mod") == 0 || strcmp(ext, "mps") == 0 || strcmp(ext, "lpt") == 0
	      || strcmp(ext, "lp") == 0)){
	    while(true){
	     sym_read_line("Type of the file ('mps'/'ampl'/'gmpl'/'lp'): ", &line);
	     if(!(strcmp(line, "mps") == 0 || strcmp(line, "ampl") == 0 ||
		  strcmp(line, "gmpl") == 0 || strcmp(line, "lp") == 0 || 
		  strcmp(line, "lpt") == 0)){
	       printf("Unknown type!\n");
	       continue; 
	     } else {
	       strcpy(ext, line);
	       break;
	     }
	   }
	 }
	 
	 if (strcmp(ext, "mps") == 0){
	    sym_free_env(env);
	    if(sym_read_mps(env, args[1])){
	       continue;
	    }
	 }else if (strcmp(ext, "lp") == 0 || strcmp(ext, "lpt") == 0){
	    sym_free_env(env);
	    if(sym_read_lp(env, args[1])){
	       continue;
	    } 
	 }else {
	   if(strcmp(args[2], "") == 0){
	     sym_read_line("Name of the data file: ", &line);
	     strcpy(args[2], line);
	   }

#if defined(HAS_READLINE) && ((RL_VERSION_MAJOR == 5 && \
			       RL_VERSION_MINOR >= 2) || \
			      (RL_VERSION_MAJOR >= 6))
	   sym_read_tilde(args[2]);	 
#endif	 	 
	 
	   if(fopen(args[2], "r") == NULL){
	     printf("Data file '%s' can't be opened\n",
		    args[2]);
	     continue;
	   }
	   sym_free_env(env);
	   if(sym_read_gmpl(env, args[1], args[2])){
	     continue;
	   }
	   
	 }
       } else if(strcmp(args[0], "solve") == 0 || 
		 strcmp(args[0], "lpsolve") == 0){
	 if(!env->mip->n){
	   printf("No loaded problem. Use 'load' to read in a problem!\n");
	   continue;
	 } 
	 if(strcmp(args[0], "solve") == 0){
	   start_time = wall_clock(NULL);
	   printf("\n");
	   if (env->mip->obj2 != NULL){
	      termcode = sym_mc_solve(env);
	   } else {
	      termcode = sym_solve(env);
	   }
	   finish_time = wall_clock(NULL);
	 } else {
	   is_int = env->mip->is_int;
	   env->mip->is_int  = (char *)   calloc(CSIZE, env->mip->n);
	   start_time = wall_clock(NULL);
	   printf("\n");
	   if (env->mip->obj2 != NULL){
	      termcode = sym_mc_solve(env);
	   } else {
	      termcode = sym_solve(env);
	   }
	   finish_time = wall_clock(NULL);
	   env->mip->is_int = is_int;
	   is_int = 0;
	 }
       } else if (strcmp(args[0], "display") == 0){

	 if(strcmp(args[1], "") == 0){
	   printf("Please type 'help'/'?' to see the display options!\n");
	 }

	 while (true){

	   if(strcmp(args[1], "") == 0){
	     main_level = 1;
	     sym_read_line("SYMPHONY\\Display: ", &line);	 
	     sscanf(line, "%s%s", args[1], args[2]);
       	     last_level = 1;
	     if (strcmp(args[2], "") == 0){
		last_level = 1;
	     }
	   } else {
	      last_level = 0;
	   }

	   if (strcmp(args[1], "help") == 0 || strcmp(args[1], "?") == 0) {
	     sym_help("display_help");
	   } else if (strcmp(args[1], "solution") == 0 || 
		      strcmp(args[1], "obj") == 0 
		      || strcmp(args[1], "stats") == 0){
	     if(!env->mip->n){
	       printf("No loaded problem! "
		      "Use 'load' in the main menu to read in a problem!\n");
	       strcpy(args[1], "");
	     } 
	     if(strcmp(args[1], "solution") == 0){
		int display = TRUE;
		switch(env->termcode){
		 case TM_NO_SOLUTION:
		   printf("Problem was found infeasible!\n");
		   display = FALSE;
		   break;
		 case TM_UNBOUNDED:
		   printf("Problem was found to be unbounded!\n");
		   display = FALSE;
		   break;
		 case TM_NODE_LIMIT_EXCEEDED:		    
		    printf("Node limit reached!\n");		    
		    break;
		 case TM_FOUND_FIRST_FEASIBLE:    
		    printf("First feasible solution found!\n");
		    break;
		 case TM_TIME_LIMIT_EXCEEDED:   
		    printf("Time limit reached!\n");
		    break;
		 case TM_TARGET_GAP_ACHIEVED:
		    printf("Target gap achieved!\n");
		    break;
		 case TM_OPTIMAL_SOLUTION_FOUND:
		    printf("Optimal Solution found!\n");
		    break;
		 case SOMETHING_DIED:
		 case TM_ERROR__NUMERICAL_INSTABILITY:  
		 case TM_ERROR__NO_BRANCHING_CANDIDATE:
		 case TM_ERROR__ILLEGAL_RETURN_CODE:
		 case TM_ERROR__COMM_ERROR:
		 case TM_ERROR__USER:
		    printf("Error in displaying solution! \n"); 
		    printf(  "* Terminated abnormally with error message %i *\n",
			     termcode);		      
		 default:
		    display = FALSE;		    
		    break;		    
		}
		if(display){
		   if(env->best_sol.has_sol){
		      if (env->mip->colname){ 
			 printf("+++++++++++++++++++++++++++++++++++++++++++++++\n");
			 printf("Nonzero column names and values in the solution\n");
			 printf("+++++++++++++++++++++++++++++++++++++++++++++++\n");
			 for(j = 0; j<env->best_sol.xlength; j++){		      
			    printf("%8s %10.10f\n", 
				   env->mip->colname[env->best_sol.xind[j]],
				   env->best_sol.xval[j]);
			 }
			 printf("\n");
		      }else{
			 printf("+++++++++++++++++++++++++++++++++++++++++++++++\n");
			 printf("User indices and values in the solution\n");
			 printf("+++++++++++++++++++++++++++++++++++++++++++++++\n");
			 for(j = 0; j<env->best_sol.xlength; j++){		      
			    printf("%7d %10.10f\n", env->best_sol.xind[j], 
				   env->best_sol.xval[j]);
			 }			    
			 printf("\n");
		      }
		   } else{
		      printf("Error in displaying solution!\n");
		   }
		}
		strcpy(args[1], ""); 		   
	     } else if (strcmp(args[1], "obj") == 0){
		if(sym_get_obj_val(env, &objval)){
		   printf("Error in displaying objective value!\n" 
			  "The problem is either infeasible " 
			  "or has not been solved yet!\n");
		 strcpy(args[1], "");
		 //		 continue;
	       } else { 
		 printf("Objective Value: %f\n", objval);
	       }
	       strcpy(args[1], "");	       
	     } else if (strcmp(args[1], "stats") == 0){
	       initial_time  = env->comp_times.readtime;
	       initial_time += env->comp_times.ub_overhead + 
		 env->comp_times.ub_heurtime;
	       initial_time += env->comp_times.lb_overhead + 
		 env->comp_times.lb_heurtime;
	       
	       if (env->warm_start){
		  print_statistics(&(env->warm_start->comp_times), 
				   &(env->warm_start->stat),
				   NULL,
				   env->warm_start->ub, env->warm_start->lb, 
				   initial_time, start_time, finish_time,
				   env->mip->obj_offset, env->mip->obj_sense,
				   env->warm_start->has_ub,NULL, 0);
		  printf("\n");
	       }else{
		  printf("No statistics! Either the solution process"
			 "terminated in preprocessing or\n"
			 "the problem has not been solved yet!\n");
	       }
	     }
	     strcpy(args[1], "");	       
	   } else if (strcmp(args[1], "parameter") == 0){

	     if(strcmp(args[2], "") == 0){
	       printf("Please type 'help'/'?' " 
		      "to see the list of available parameters!\n");
	     }
	     while(true){

	       if (strcmp(args[2], "") == 0){
		 main_level = 3;
		 sym_read_line("SYMPHONY\\Display\\Parameter: ", &line);
		 strcpy(args[2], line);	
		 if (last_level != 0 || last_level !=1)
		    last_level = 2;
	       }

	       if (strcmp(args[2], "help") == 0 || strcmp(args[2], "?") == 0) {
		 sym_help("display_param_help");
	       } else if (strcmp(args[2], "back") == 0){
		 break;
	       } else if ((strcmp(args[2], "quit") == 0) ||
			  (strcmp(args[2], "exit") == 0)){ 
		 terminate = TRUE;
		 break;
	       } else {
		 if (sym_get_int_param(env, args[2], &int_value) == 0){
		   printf("The value of %s: %i\n", args[2], int_value);
		 } else if ( sym_get_dbl_param(env, args[2], &dbl_value) == 0){
		   printf("The value of %s: %f\n", args[2], dbl_value);
		 }else {
		   printf("Unknown parameter/command!\n");		   
		 }
	       }
	       strcpy(args[1], "");
	       strcpy(args[2], "");
	       if (last_level < 2) break; 
	     }
	     if (terminate) break;	        	   
	   } else if (strcmp(args[1], "back") == 0){
	     break;
	   } else if ((strcmp(args[1], "quit") == 0) ||
		      (strcmp(args[1], "exit") == 0)){
	     terminate = TRUE;
	     break;
	   } else {
	     printf("Unknown command!\n");
	   }     
	   strcpy(args[1], "");
	   strcpy(args[2], "");
	   if(last_level < 1) break; 
	 }
       } else if (strcmp(args[0], "set") == 0){
	 if(strcmp(args[1], "") == 0){
	   printf("Please type 'help'/'?' to see the list of parameters!\n");
	 }

	 while (true){
	   if(strcmp(args[1], "") == 0){
	     main_level = 2;
	     sym_read_line("SYMPHONY\\Set: ", &line);	 
	     sscanf(line, "%s%s", args[1], args[2]);
	     last_level = 1;
	   } else{
	     last_level = 0;
	   }

	   if (strcmp(args[1], "help") == 0 || strcmp(args[1], "?") == 0) {
	     sym_help("set_help");
	   } else if (strcmp(args[1], "back") == 0){
	     break;
	   } else if ((strcmp(args[1], "quit") == 0) ||
		      (strcmp(args[1], "exit") == 0)){
	     terminate = TRUE;
	     break;
	   } else if (strcmp(args[1], "param_file") == 0){

	     if(strcmp(args[2], "") == 0){
	       sym_read_line("Name of the parameter file: ", &line);
	       strcpy(args[2], line);
	     }

#if defined(HAS_READLINE) && ((RL_VERSION_MAJOR == 5 && \
			       RL_VERSION_MINOR >= 2) ||\
			      (RL_VERSION_MAJOR >= 6))
	     sym_read_tilde(args[2]);	 
#endif	 	 

	     if ((f = fopen(args[2], "r")) == NULL){
	       printf("Parameter file '%s' can't be opened\n",
		      args[2]);
	       if(last_level == 1){
		 strcpy(args[1], "");
		 strcpy(args[2], "");
		 continue;
	       }
	       else break;
	     }

	     /*read in parameter file*/
	     while(NULL != fgets(args[2], MAX_LINE_LENGTH, f)){ 
	       sscanf(args[2],"%s%s", param, value);
	       if(set_param(env, args[2]) == 0){
		 printf("Setting %s to: %s\n", param, value); 
	       } else {
		 printf("Unknown parameter %s: !\n", param);
		 continue;
	       }	     
	     }
	     fclose(f);

	   } else {
	    
	     if(strcmp(args[2], "") == 0){
	       sym_read_line("Value of the parameter: ", &line);
	       strcpy(args[2], line);
	     }
	     strcpy(args[0], "");
	     sprintf(args[0], "%s %s", args[1], args[2]);  
	     if(set_param(env, args[0]) == 0){
	       printf("Setting %s to: %s\n", args[1], args[2]); 
	     } else {
	       printf("Unknown parameter/command!\n");
	     }
	     if(last_level <1) break;
	     else{
	       strcpy(args[1], "");
	       strcpy(args[2], "");	       
	       continue;
	     }
	   }
	   if(last_level <1) break;
	   strcpy(args[1], "");
	   strcpy(args[2], "");	       
	 }
       } else if (strcmp(args[0], "reset") == 0){
	 printf("Resetting...\n");
	 sym_close_environment(env);
	 env = sym_open_environment();
	 sym_set_int_param(env, "verbosity", -1);
       } else if ((strcmp(args[0], "quit") == 0) ||
		  (strcmp(args[0], "exit") == 0)){
	 break;
       } else {
	 printf("Unknown command!\n");
	 continue;
       }

       if(terminate) break;

     }
   } 
   sym_close_environment(env);
  
   return(0);
}    

/*===========================================================================*\
\*===========================================================================*/

int sym_help(const char *line)
{    
  if(strcmp(line, "main_help") == 0){

    printf("\nList of main commands: \n\n");
    printf("load      : read a problem in mps, ampl or lp format\n"
	   "solve     : solve the problem\n"
	   "lpsolve   : solve the lp relaxation of the problem\n"
	   "set       : set a parameter\n"
	   "display   : display optimization results and stats\n"
	   "reset     : restart the optimizer\n"
	   "help      : show the available commands/params/options\n\n"

	   "quit/exit : leave the optimizer\n\n");
    
  } else if (strcmp(line, "set_help") == 0 || strcmp(line, "display_param_help") == 0){

    printf("\n\nList of parameters: \n\n"); 
    printf("verbosity                          : set verbosity (default: -1)\n"
	   "upper_bound                        : use an initial upper bound\n"
	   "find_first_feasible                : whether to find the first feasible solution or\n"
	   "                                     to solve the optimality (default: 0) \n"
	   "generate_cgl_cuts                  : whether or not to use cgl cuts (default: 1)\n"
	   "generate_cgl_gomory_cuts           : set generation level of cgl gomory cuts (default: 0)\n"
	   "generate_cgl_redsplit_cuts         : set generation level of cgl redsplit cuts (default: -1)\n"
	   "generate_cgl_knapsack_cuts         : set generation level of cgl knapsack cuts (default: 0)\n"
	   "generate_cgl_oddhole_cuts          : set generation level of cgl oddhole cuts (default: 0)\n"
	   "generate_cgl_probing_cuts          : set generation level of cgl probing cuts (default: 0)\n"
	   "generate_cgl_clique_cuts           : set generation level of cgl clique cuts (default: 0)\n"	   
	   "generate_cgl_mir_cuts              : set generation level of cgl mixed integer rounding cuts\n" 
           "                                     (default: -1)\n"
	   "generate_cgl_twomir_cuts            : set generation level of cgl two-step mixed integer rounding cuts\n" 
           "                                     (default: -1)\n"
 	   "generate_cgl_flow_and_cover_cuts   : set generation level of cgl flow and cover cuts (default: 0)\n"
	   "generate_cgl_rounding_cuts         : set generation level of cgl rounding cuts (default: -1)\n"
	   "generate_cgl_lift_and_project_cuts : set generation level of cgl lift and project cuts (default: -1)\n"
	   "generate_cgl_landp_cuts            : set generation level of cgl lift and project cuts (default: -1)\n"
	   "node_selection_rule                : set the node selection rule/search strategy (default: 5)\n"
	   "strong_branching_candidate_num     : set the stong branching candidates number (default: var)\n"
	   "compare_candidates_default         : set the rule to compare the candidates (defualt: 2)\n"
	   "select_child_default               : set the rule to select the children (default: 0)\n"
	   "diving_threshold                   : set diving threshold (default: 0)\n"
	   "diving_strategy                    : set diving strategy (default: 0)\n"
	   "do_reduced_cost_fixing             : whether ot not to use reduced cost fixing (default: 1)\n"
	   "time_limit                         : set the time limit\n"
	   "node_limit                         : set the node limit\n"
	   "gap_limit                          : set the target gap between the lower and upper bound\n"
           "param_file                         : read parameters from a parameter file\n"
	   "do_primal_heuristic                : whether or not to use primal heuristics\n\n"
	   "should_use_rel_br                  : whether or not to use reliability branching\n\n"
	   "prep_level                         : pre-processing level\n\n"
	   "tighten_root_bounds                : whether to tighten root bounds \n\n"
	   "limit_strong_branching_time        : whether to limit time spent in strong branching \n\n"
	   "back                               : leave this menu\n"
	   "quit/exit                          : leave the optimizer\n\n");
					    
  } else if (strcmp(line, "display_help") == 0){

    printf("\nList of display options: \n\n");
    printf("solution     : display the column values\n"
	   "obj          : display the objective value\n"
	   "stats        : display the statistics\n"
	   "parameter    : display the value of a parameter\n\n"

	   "back         : leave this menu\n"
	   "quit/exit    : leave the optimizer\n\n");
  }

  return(0);
}

/*===========================================================================*\
\*===========================================================================*/

int sym_read_line(const char *prompt, char **input)
{

#if defined(HAS_READLINE) && ((RL_VERSION_MAJOR == 5 && \
			       RL_VERSION_MINOR >= 2) || \
			      (RL_VERSION_MAJOR >= 6))

  if (*input) FREE(*input);

  while(true) {
    *input = readline(prompt);
    if (**input) {      
      add_history(*input);
      if((*input)[strlen(*input)-1] == ' '){
	(*input)[strlen(*input)-1] = 0;
      }
      break;
    } else continue;
  }

#else
  
  int i;

  if (*input) FREE(*input);
  char * getl = (char *)malloc(CSIZE* (MAX_LINE_LENGTH +1));
   
  while(true){
     strcpy(getl, "");
     printf("%s",prompt);
     fflush(stdout);
     fgets(getl, MAX_LINE_LENGTH, stdin);

     if(getl[0] == '\n' ) {
	continue;
     }else {
	for (i=0; i<strlen(getl); i++){
	   if ( getl[i] == '\n' ) {
	      getl[i] = '\0';
	      break;
	   }
	}
	break;
     }
  }
  *input = getl;
  
#endif

  return (0);
}

/*===========================================================================*\
\*===========================================================================*/
int sym_free_env(sym_environment *env){
   if(env->mip->n){
      free_master_u(env);
      env->ub = 0;
      env->lb = -MAXDOUBLE;
      env->has_ub = FALSE;
      env->termcode = TM_NO_SOLUTION;
      strcpy(env->par.infile, "");
      strcpy(env->par.datafile, "");
      env->mip = (MIPdesc *) calloc(1, sizeof(MIPdesc));
   }
   return 0;
} 
/*===========================================================================*\
\*===========================================================================*/
#if defined(HAS_READLINE) && ((RL_VERSION_MAJOR == 5 && \
			       RL_VERSION_MINOR >= 2) || \
			      (RL_VERSION_MAJOR >= 6))

void sym_initialize_readline()
{
  //  rl_readline_name = "SYMPHONY";
  rl_attempted_completion_function = sym_completion;
}

/*===========================================================================*\
\*===========================================================================*/

char **sym_completion(const char *text, int start, int end)
{
  char **matches;
  char key[2][MAX_LINE_LENGTH+1];
  matches = (char **)NULL;

  strcpy(key[0], "");
  strcpy(key[1], "");

  sscanf(rl_line_buffer, "%s%s", key[0], key[1]);
  comp_level = 0;
 
  if(main_level == 0){
    if(strcmp(key[0], "display") == 0){
      comp_level = 1;
      if(strcmp(key[1], "parameter") == 0){
	comp_level = 3;
      }
    }else if(strcmp(key[0], "set") == 0){
      comp_level = 2;
    }else if(strcmp(key[0], "parameter") == 0){
      comp_level = 3;
    }	     
  } else if(main_level == 1){
    comp_level = 1;
    if(strcmp(key[0], "parameter") == 0){    
      comp_level = 3;
    }
  } else {
    comp_level = main_level;
  }

  if(!(strcmp(key[0], "load") == 0 || strcmp(key[0], "param_file") == 0 ||
       strcmp(key[1], "param_file") == 0 )){
    matches = rl_completion_matches (text, command_generator);
  }
  return (matches);
}

/*===========================================================================*\
\*===========================================================================*/

char *command_generator (const char *text, int state)
{
  static int list_index, len;
  char *name;

  if(!state){
    list_index = 0;
    len = strlen (text);
  }
  
  if(comp_level == 0 ){
    while (name = main_commands[list_index].name)
      {
	list_index++;
	
	if (strncmp (name, text, len) == 0)
	  return (alloc_str(name));
      }
  } else if (comp_level == 1){
        while (name = display_commands[list_index].name)
      {
	list_index++;
	
	if (strncmp (name, text, len) == 0)
	  return (alloc_str(name));
      }
  } else{
    //  printf("comp_level: %i\n", comp_level);
        while (name = parameter_commands[list_index].name)
      {
	list_index++;
	
	if (strncmp (name, text, len) == 0)
	  return (alloc_str(name));
      }
  }


  /* If no names matched, then return NULL. */
  return ((char *)NULL);
}


/*===========================================================================*\
\*===========================================================================*/

char *alloc_str(char *s)
{
  char *r = NULL;
  int len = strlen(s);
  if(len){
    r = (char *)malloc(CSIZE*(len+1));
    strcpy (r, s);
  }
  return (r);
}

/*===========================================================================*\
\*===========================================================================*/

void sym_read_tilde(char input[])
{
   char temp;
   char temp_inp[MAX_LINE_LENGTH+1];
   struct passwd *pwd = 0 ;

   if(*input){
      sscanf(input, "%c", &temp);
      if(temp == '~'){
	 pwd = getpwuid(getuid());
	 if(pwd != NULL){
	    strcpy(temp_inp, input);
	    sprintf(input, "%s%s", pwd->pw_dir, &temp_inp[1]);
	 }
      }	    
   }
}

#endif
#endif



