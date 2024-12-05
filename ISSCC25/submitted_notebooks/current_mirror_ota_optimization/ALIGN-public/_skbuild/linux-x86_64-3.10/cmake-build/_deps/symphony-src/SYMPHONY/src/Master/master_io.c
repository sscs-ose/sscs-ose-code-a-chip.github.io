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

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include "sym_timemeas.h"
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_types.h"
#include "sym_lp_params.h"
#include "sym_master.h"
#include "sym_master_u.h"
#undef SHOULD_SHOW_MEMORY_USAGE

/*===========================================================================*/

/*===========================================================================*\
 * This file contains I/O functions for the master process.
\*===========================================================================*/

/*===========================================================================*/

void usage(void)
{
#ifdef USE_SYM_APPLICATION
   printf("Generic switches:\n\n");
   printf("app_name [ -f parameter_file_name ] \n\t"
#else
   printf("symphony [ -FL file ] [ -f parameter_file_name ] \n\t"
#endif
	  "[ -hd ] [-a 0/1] [-b 0/1 ] [-s cands] [-l 0/1] [ -q 0/1 ] [ -r 0/1]\n\t"
	  "[-j 0/1 ] [ -e n ] [ -i iters ] [ -t time ] [ -g gap ] [ -n nodes ]\n\t"
          "[ -u ub ] [ -p procs ] [ -k rule ] [ -v level ] [ -c rule ]\n\t"
	  "[ -m max ] [ -z n ] [-o tree_out_file] [-w 0/1]\n\t"
	  "\n\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n"
	  "\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n"
	  "\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n"
#ifndef USE_SYM_APPLICATION
	  "\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t\n\n",
	  "-F model: model should be read in from file 'model'",
	  "          (MPS format is assumed unless -D is also present)",
	  "-L model: LP format model should be read in from file 'model'",
	  "-D data: model is in AMPL format and data is in file 'data'",
	  "-T dir: run test with MIPLIB3 models",
#else
	  "\n\n",
#endif	  
	  "-h: help",
	  "-f file: read parameters from parameter file 'file'",
	  "-d: stop at first feasible solution",
	  "-a 0/1: whether to use primal heuristics",
	  "-b 0/1: whether to use reliability branching",
	  "-s cands: use at most 'cands' candidates for strong branching",
	  "-l 0/1: whether to impose a limit on strong branching time",
	  "-q 0/1: whether or not to tighten root bounds",
	  "-r 0/1: whether or not to do reduced cost tightening",
	  "-j 0/1: whether or not to generate cgl cuts",
	  "-w 0/1: whether or not to use hot starting in strong branching ",
	  "-e n: set pre-processing level to 'n'",
	  "-i iters: allow a max of 'iters' iterations in presolve",
	  "-t time: set wallclock time limit to 'time'",
	  "-g gap: set gap limit to 'gap'",
	  "-n nodes: set node limit to 'nodes'",
	  "-u ub: use initial upper bound 'ub'",
	  "-p procs: allow 'procs' additional threads or processors",
	  "-k i: use node selection rule 'i'",
	  "-v n: set verbosity to level 'n'",
	  "-c i: use rule 'i' to compare candidates",
	  "-m max: allow a max of 'max' cuts to enter per iteration",
	  "-z n: set diving threshold to 'n'",
	  "-o file: output vbc-like tree information to file 'file'");
#ifdef USE_SYM_APPLICATION
   printf("Application-specific switches:\n\n");
   printf("app_name [ -H ] [ -F file ] \n\n\t%s\n\t%s\n\t\n\n",
	  "-H: help (solver-specific switches)",
	  "-F model: model should be read in from file 'model'");
   user_usage();
#else
#endif   
}

/*===========================================================================*/
/*===========================================================================*/

int parse_command_line(sym_environment *env, int argc, char **argv)
{
   int i, tmpi;
   double tmpd;
   char line[MAX_LINE_LENGTH +1], tmp, c;
   char key[MAX_LINE_LENGTH +1], value[MAX_LINE_LENGTH +1];
   FILE *f = NULL, *f1 = NULL;
   //   str_int colgen_str[COLGEN_STR_SIZE] = COLGEN_STR_ARRAY;
   tm_params *tm_par = &env->par.tm_par;
   lp_params *lp_par = &env->par.lp_par;
   cg_params *cg_par = &env->par.cg_par;
   cp_params *cp_par = &env->par.cp_par;
   prep_params *prep_par = &env->par.prep_par;
   //dg_params *dg_par = &env->par.dg_par;

   if (argc < 2){
      usage();
      exit(0);
   }
   
   for (i = 0; i < argc; i++){
      if (!strcmp(argv[i], "-f"))
	 break;
   }
   
   if (i == argc){
      goto EXIT;
   }else{
      strncpy(env->par.param_file, argv[i+1], MAX_FILE_NAME_LENGTH);
   }
   
   if ((f = fopen(env->par.param_file, "r")) == NULL){
      (void) fprintf(stderr, "Readparams: file '%s' can't be opened\n\n",
		     env->par.param_file);
      return(ERROR__OPENING_PARAM_FILE);
   }

   printf("============= Other Parameter Settings =============\n\n");

   while (NULL != fgets(line, MAX_LINE_LENGTH, f)){  /* read in parameters */

      set_param(env, line);

      printf("%s", line);
      strcpy(key,"");
      sscanf(line,"%s%s", key, value);

      if (strcmp(key, "lp_mach_num") == 0 ||
	  strcmp(key, "TM_lp_mach_num") == 0){
	 if (tm_par->lp_mach_num){
	    char *lp_machs = (char *) malloc
	       (tm_par->lp_mach_num * (MACH_NAME_LENGTH + 1));
	    tm_par->lp_machs =
	       (char **) malloc(tm_par->lp_mach_num * sizeof(char *));
	    for (i=0; i<tm_par->lp_mach_num; i++)
	       tm_par->lp_machs[i] = lp_machs + i * (MACH_NAME_LENGTH+1);
	    for (i=0; i<tm_par->lp_mach_num; i++){
	       if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
		  fprintf(stderr, "\nio: error reading lp_machine list\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       strcpy(key, "");
	       sscanf(line, "%s%s", key, value);
	       if (strcmp(key, "TM_lp_machine") != 0){
		  fprintf(stderr, "\nio: error reading lp_machine list\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       read_string(tm_par->lp_machs[i], line, MACH_NAME_LENGTH);
	       printf("%s", line);
	    }
	 }
      }
      else if (strcmp(key, "cg_mach_num") == 0 ||
	       strcmp(key, "TM_cg_mach_num") == 0){
	 if (tm_par->cg_mach_num){
	    char *cg_machs = (char *) malloc
	       (tm_par->cg_mach_num * (MACH_NAME_LENGTH + 1));
	    tm_par->cg_machs =
	       (char **) malloc(tm_par->cg_mach_num * sizeof(char *));
	    for (i=0; i<tm_par->cg_mach_num; i++)
	       tm_par->cg_machs[i] = cg_machs + i * (MACH_NAME_LENGTH+1);
	    for (i=0; i<tm_par->cg_mach_num; i++){
	       if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
		  fprintf(stderr, "\nio: error reading cg_machine list\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       strcpy(key, "");
	       sscanf(line, "%s%s", key, value);
	       if (strcmp(key, "TM_cg_machine") != 0){
		  fprintf(stderr, "\nio: error reading cg_machine list\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       read_string(tm_par->cg_machs[i], line, MACH_NAME_LENGTH);
	       printf("%s", line);
	    }
	 }
      }
      else if (strcmp(key, "cp_mach_num") == 0 ||
	       strcmp(key, "TM_cp_mach_num") == 0){
	 if (tm_par->cp_mach_num){
	    char *cp_machs = (char *) malloc
	       (tm_par->cp_mach_num * (MACH_NAME_LENGTH + 1));
	    tm_par->cp_machs =
	       (char **) malloc(tm_par->cp_mach_num * sizeof(char *));
	    for (i=0; i<tm_par->cp_mach_num; i++)
	       tm_par->cp_machs[i] = cp_machs + i * (MACH_NAME_LENGTH+1);
	    for (i=0; i<tm_par->cp_mach_num; i++){
	       if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
		  fprintf(stderr, "\nio: error reading cp_machine list\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       strcpy(key, "");
	       sscanf(line, "%s%s", key, value);
	       if (strcmp(key, "TM_cp_machine") != 0){
		  fprintf(stderr, "\nio: error reading cp_machine list\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       read_string(tm_par->cp_machs[i], line, MACH_NAME_LENGTH);
	       printf("%s", line);
	    }
	 }
      }
      else if (strcmp(key, "keep_description_of_pruned") == 0 ||
	       strcmp(key, "TM_keep_description_of_pruned") == 0){
	 if (tm_par->keep_description_of_pruned == KEEP_ON_DISK_FULL ||
	     tm_par->keep_description_of_pruned == KEEP_ON_DISK_VBC_TOOL){
	    if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
	       printf("No pruned node file!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "pruned_node_file_name") != 0){
	       printf("Need pruned_node_file_name next!!!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(tm_par->pruned_node_file_name, value);
	    if (!(f1 = fopen(tm_par->pruned_node_file_name, "w"))){
	       printf("\nError opening pruned node file\n\n");
	    }else{
	       if (tm_par->keep_description_of_pruned == KEEP_ON_DISK_FULL){
		  fprintf(f1, "******* Pruned Node Log File *******\n\n");
	       }else{
		  fprintf(f1, "#TYPE: COMPLETE TREE\n");
		  fprintf(f1, "#TIME: NOT\n");
		  fprintf(f1, "#BOUNDS: NONE\n");
		  fprintf(f1, "#INFORMATION: EXCEPTION\n");
		  fprintf(f1, "#NODE_NUMBER: NONE\n");
	       }
	       fclose(f1);
	    }
	 }
      }
      else if (strcmp(key, "warm_start") == 0 ||
	       strcmp(key, "TM_warm_start") == 0){
	 if ((env->par.warm_start = tm_par->warm_start)){
	    if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
	       printf("No warm start tree file!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "warm_start_tree_file_name") != 0){
	       printf("Need warm_start_tree_file_name next!!!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(tm_par->warm_start_tree_file_name, value);
	    if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
	       printf("No warm start cut file!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "warm_start_cut_file_name") != 0){
	       printf("Need warm_start_cut_file_name next!!!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(tm_par->warm_start_cut_file_name, value);
	 }
      }
      else if (strcmp(key, "vbc_emulation") == 0 ||
	       strcmp(key, "TM_vbc_emulation") == 0){
	 if (tm_par->vbc_emulation == VBC_EMULATION_FILE || 
	       tm_par->vbc_emulation == VBC_EMULATION_FILE_NEW){
	    if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
	       printf("No vbc emulation file!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "vbc_emulation_file_name") != 0){
	       printf("Need vbc_emulation_file_name next!!!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(tm_par->vbc_emulation_file_name, value);
	    if (!(f1 = fopen(tm_par->vbc_emulation_file_name, "w"))){
	       printf("\nError opening vbc emulation file\n\n");
	    }else{
	       fprintf(f1, "#TYPE: COMPLETE TREE\n");
	       fprintf(f1, "#TIME: SET\n");
	       fprintf(f1, "#BOUNDS: NONE\n");
	       fprintf(f1, "#INFORMATION: STANDARD\n");
	       fprintf(f1, "#NODE_NUMBER: NONE\n");
	       if (tm_par->vbc_emulation == VBC_EMULATION_FILE_NEW) {
		  fprintf(f1, "# ");
	       }
	       fprintf(f1, "00:00:00.00 N 0 1 %i\n", VBC_CAND_NODE);
	       fclose(f1);
	    }
	 }else if (tm_par->vbc_emulation == VBC_EMULATION_LIVE){
	    printf("$#TYPE: COMPLETE TREE\n");
	    printf("$#TIME: SET\n");
	    printf("$#BOUNDS: NONE\n");
	    printf("$#INFORMATION: STANDARD\n");
	    printf("$#NODE_NUMBER: NONE\n");
	    printf("$N 0 1 %i\n", VBC_CAND_NODE);
	 }
      }
      else if (strcmp(key, "logging") == 0 ||
	       strcmp(key, "TM_logging") == 0){
	 if (tm_par->logging){
	    if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
	       printf("No tree log file!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "tree_log_file_name") != 0){
	       printf("tree_log_file_name next!!!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(tm_par->tree_log_file_name, value);
	    if (tm_par->logging != VBC_TOOL){
	       if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
		  printf("No cut log file!\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       strcpy(key, "");
	       sscanf(line, "%s%s", key, value);
	       if (strcmp(key, "cut_log_file_name") != 0){
		  printf("Need cut_log_file_name next!!!\n\n");
		  return(ERROR__PARSING_PARAM_FILE);
	       }
	       strcpy(tm_par->cut_log_file_name, value);
	    }
	 }
      }
      else if (strcmp(key, "cp_warm_start") == 0 ||
	       strcmp(key, "CP_warm_start") == 0){
	 if (cp_par->warm_start){
	    if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
	       printf("No cut pool warm start file!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "cp_warm_start_file_name") != 0){
	       printf("Need cp_warm_start_file_name next!!!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(cp_par->warm_start_file_name, value);
	 }
      }
      else if (strcmp(key, "cp_logging") == 0 ||
	       strcmp(key, "CP_logging") == 0){
	 if ((tm_par->cp_logging = cp_par->logging)){
	    if (fgets(line, MAX_LINE_LENGTH, f) == NULL){
	       printf("No cut pool log file!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(key, "");
	    sscanf(line, "%s%s", key, value);
	    if (strcmp(key, "cp_log_file_name") != 0){
	       printf("Need cp_log_file_name next!!!\n\n");
	       return(ERROR__PARSING_PARAM_FILE);
	    }
	    strcpy(cp_par->log_file_name, value);
	 }
      }
   }

   printf("\n====================================================\n\n");
   
 EXIT:
   
   for (i = 1; i < argc; i++){
      sscanf(argv[i], "%c %c", &tmp, &c);
      if (tmp != '-')
	 continue;
      switch (c) {
       case '-':
	 if (!strcmp(argv[i], "--version")){
	    sym_version();
	    exit(0);
	 }
	 if (!strcmp(argv[i], "--help")){
	    usage();
	    exit(0);
	 }
	 if (!strcmp(argv[i], "--args")){
	    printf("SYMPHONY was called with the following arguments:\n");
	    printf("%s ", argv[0]);
	    for (i = 1; i < argc; i++){
	       sscanf(argv[i], "%c", &tmp);
	       if (tmp == '-')
		  printf("\n");
	       printf("%s ", argv[i]);
	    }
	    printf("\n\n");
	 }
	 break;
       case 'h':
	 usage();
	 exit(0);
       case 'H':
#ifdef USE_SYM_APPLICATION
	  user_usage();
#else
	  printf("master [ -H ] [ -F file ] \n\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\n",
		 "-H: help (solver-specific switches)",
		 "-F model: model should be read in from file 'model'",
		 "          (MPS format is assumed unless -D is also present)",
		 "-L model: LP format model should be read in from file 'model'",
		 "-D data: model is in AMPL format and data is in file 'data'");
#endif 
	  exit(0);
       case 'a':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->do_primal_heuristic = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'd':
	 lp_par->find_first_feasible = TRUE;
	 break;
       case 'e':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       prep_par->level = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'g':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%lf", &tmpd)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       tm_par->gap_limit = tmpd;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'q':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->do_reduced_cost_fixing = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'r':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       tm_par->tighten_root_bounds = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 't':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%lf", &tmpd)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->time_limit = tm_par->time_limit = tmpd;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'b':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->should_use_rel_br = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'u':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%lf", &tmpd)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       env->ub = tmpd;
	       env->has_ub = TRUE;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'p':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
#if defined(COMPILE_IN_LP)
#ifdef _OPENMP
	       tm_par->max_active_nodes = tmpi + 1;
#else
	       if (tmpi > 1){
		  printf("\nWarning: Trying to use multiple processors with ");
		  printf("sequential build...\n");
		  tm_par->max_active_nodes = 1;
	       }
#endif
#else
	       tm_par->max_active_nodes = tmpi;
#endif
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'n':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       tm_par->node_limit = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'v':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       prep_par->verbosity = tm_par->verbosity = lp_par->verbosity =
               cg_par->verbosity = cp_par->verbosity = env->par.verbosity =
               tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
 	 break;
       case 's':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->strong_branching_cand_num_min =
	       lp_par->strong_branching_cand_num_max = tmpi;
	       lp_par->strong_branching_red_ratio = 0;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'c':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->compare_candidates_default = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'k':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       tm_par->node_selection_rule = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'm':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->max_cut_num_per_iter = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'l':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->limit_strong_branching_time = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
       case 'i':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->max_presolve_iter = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'f':
	 if (i < argc - 1){
	    sscanf(argv[i+1], "%c", &tmp);
	    if (tmp == '-'){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       strncpy(env->par.param_file, argv[i+1], MAX_FILE_NAME_LENGTH);
	       i++;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'j':
       if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->cgl.generate_cgl_cuts = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'z':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%lf", &tmpd)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       tm_par->diving_threshold = tmpd;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'o':
	 if (i < argc - 1){
	    sscanf(argv[i+1], "%c", &tmp);
	    if (tmp== '-') {
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       strncpy(tm_par->vbc_emulation_file_name, argv[i+1], MAX_FILE_NAME_LENGTH);
	       tm_par->vbc_emulation = VBC_EMULATION_FILE_NEW;
	       i++;
	       FILE *f2;
	       if (!(f2 = fopen(tm_par->vbc_emulation_file_name, "w"))){
		  printf("\nError opening vbc emulation file\n\n");
	       }else{
		  fprintf(f2,"# ");
		  fprintf(f2, "file created\n");
		  fclose(f2); 
	       }
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       case 'w':
	 if (i < argc - 1){
	    if (!sscanf(argv[i+1], "%i", &tmpi)){
	       printf("Warning: Missing argument to command-line switch -%c\n",
		      c);
	    }else{
	       i++;
	       lp_par->use_hot_starts = tmpi;
	    }
	 }else{
	    printf("Warning: Missing argument to command-line switch -%c\n",c);
	 }
	 break;
       default:
	 if (c < 'A'){
	    printf("Warning: Ignoring unrecognized command-line switch -%c\n",
		   c);
	 }
	 break;
      };
   }

   /*Sanity checks*/

   if (cp_par->block_size >cp_par->max_number_of_cuts){
      printf("io: Cut pool block size is too big -- adjusting\n");
      cp_par->block_size = cp_par->max_number_of_cuts;
   }

   if (cp_par->min_to_delete > cp_par->max_number_of_cuts -
                               cp_par->cuts_to_check){
      printf("io: Cut pool min to delete is too big -- adjusting\n");
      cp_par->min_to_delete = cp_par->max_number_of_cuts -
	                      cp_par->cuts_to_check;
   }

   /*if (tm_par->price_in_root &&
       tm_par->colgen_strat[0] != (FATHOM__DO_NOT_GENERATE_COLS__SEND |
				   BEFORE_BRANCH__DO_NOT_GENERATE_COLS)){
      printf("io: pricing in root is asked for but colums are to be\n");
      printf("    generated in the 1st phase -- adjusting colgen_strat[0]\n");
      tm_par->colgen_strat[0] = (FATHOM__DO_NOT_GENERATE_COLS__SEND |
				 BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
   }*/

   if (f)
      fclose(f);

   return(FUNCTION_TERMINATED_NORMALLY);
}

/*===========================================================================*/
/*===========================================================================*/

void read_string(char *target, char *line, int maxlen)
{
   char key[MAX_LINE_LENGTH +1], value[MAX_LINE_LENGTH +1], *quote1, *quote2;
   int len;

   if (sscanf(line, "%s%s", key, value) != 2)
      READPAR_ERROR(key);

   if (value[0] != '"'){ /* the string is not quoted */
      quote1 = value;
      len = (int)strlen(quote1);
   }else{ /* the string is quoted */
      quote1 = strchr(line, '"');
      quote2 = strrchr(line,'"');
      if (quote1 == quote2)
	 READPAR_ERROR(key);
      quote1++;
      len = (int)(quote2 - quote1);
   }
   
   if (len > maxlen)
      READPAR_ERROR(key);
   if (len > 0)
      strncpy(target, quote1, len);
   target[len] = 0;
   if (strchr(target, '{') || strchr(target, '}'))
      READPAR_ERROR(key);
}

/*===========================================================================*/
/*===========================================================================*/

void print_statistics(node_times *tim, problem_stat *stat, 
                      lp_stat_desc *lp_stat, double ub,
		      double lb, double initial_time, double start_time,
		      double finish_time, double obj_offset, char obj_sense, 
		      int has_ub, sp_desc *solpool, int output_mode)
{
   double gap = 0.0;
   
#if 0
   static str_int nfstatus[4] = {
      {"NF_CHECK_ALL"           , NF_CHECK_ALL }
      , {"NF_CHECK_AFTER_LAST"    , NF_CHECK_AFTER_LAST }
      , {"NF_CHECK_UNTIL_LAST"    , NF_CHECK_UNTIL_LAST }
      , {"NF_CHECK_NOTHING"       , NF_CHECK_NOTHING }
   };
#endif
   
   if (tim){
      initial_time += tim->communication;
      initial_time += tim->lp;
      initial_time += tim->lp_setup;
      initial_time += tim->separation;
      initial_time += tim->fixing;
      initial_time += tim->pricing;
      initial_time += tim->strong_branching;
      initial_time += tim->cut_pool;
      initial_time += tim->primal_heur;
#if !defined(_MSC_VER)  /* FIXME: CPU timing doesn't work in Windows */
      printf("======================= CP Timing ===========================\n");
      printf("  Cut Pool                  %.3f\n", tim->cut_pool);
#endif
      printf("====================== LP/CG Timing =========================\n");
#if !defined(_MSC_VER)  /* FIXME: CPU timing doesn't work in Windows */
      printf("  LP Solution Time          %.3f\n", tim->lp);
      printf("  LP Setup Time             %.3f\n", tim->lp_setup);
      printf("  Variable Fixing           %.3f\n", tim->fixing);
      printf("  Pricing                   %.3f\n", tim->pricing);
      printf("  Strong Branching          %.3f\n", tim->strong_branching);
      printf("  Separation                %.3f\n", tim->separation); 
      printf("  Primal Heuristics         %.3f\n", tim->primal_heur); 
      printf("  Communication             %.3f\n", tim->communication);
      printf("=================== Parallel Overhead ======================\n");
      printf("  Communication         %.3f\n", tim->communication);
      printf("  Ramp Up Time (TM)     %.3f\n", tim->ramp_up_tm);
#ifndef COMPILE_IN_LP
      printf("  Ramp Up Time (LP)     %.3f\n", tim->ramp_up_lp);
#endif
      printf("  Ramp Down Time        %.3f\n", tim->ramp_down_time);
#ifndef COMPILE_IN_LP
      printf("  Idle Time (Node Pack) %.3f\n", tim->start_node);
      printf("  Idle Time (Nodes)     %.3f\n", tim->idle_node);
      printf("  Idle Time (Names)     %.3f\n", tim->idle_names);
      printf("  Idle Time (Diving)    %.3f\n", tim->idle_diving);
      printf("  Idle Time (Cuts)      %.3f\n", tim->idle_cuts);
#endif
#endif
   }
#if !defined(_MSC_VER)
   printf("  Total User Time              %.3f\n", initial_time);
#endif
   printf("  Total Wallclock Time         %.3f\n\n", finish_time -
	  start_time);
   if (stat){
      printf("====================== Statistics =========================\n");
      printf("Number of created nodes :       %i\n", stat->created);
      printf("Number of analyzed nodes:       %i\n", stat->analyzed);
      printf("Depth of tree:                  %i\n", stat->max_depth);
      printf("Size of the tree:               %i\n", stat->tree_size);
      if (solpool) {
	 printf("Number of solutions found:      %i\n", solpool->total_num_sols_found);
	 printf("Number of solutions in pool:    %i\n", solpool->num_solutions);
      }
#ifdef SHOULD_SHOW_MEMORY_USAGE
      printf("Virtual memory used (MB):       %.2f\n", stat->max_vsize);
#endif
      
#if 0
      printf("Leaves before trimming:         %i\n",
	     stat->leaves_before_trimming);
      printf("Leaves after trimming:          %i\n", stat->leaves_after_trimming);
      printf("Repriced root's nf_status:      %s\n",
	     nfstatus[(int)stat->nf_status].str);
      printf("Not fixed variable num:         %i\n", stat->vars_not_priced);
#endif
      printf("Number of Chains:               %i\n", stat->chains);
      printf("Number of Diving Halts:         %i\n", stat->diving_halts);
      printf("Number of cuts in cut pool:     %i\n", stat->cuts_in_pool);
      if (stat->root_lb > -MAXDOUBLE){
	 if (obj_sense == SYM_MAXIMIZE){
	    printf("Upper Bound in Root:            %.3f\n",
		   -stat->root_lb + obj_offset);
	 }else{
	    printf("Lower Bound in Root:            %.3f\n",
		   stat->root_lb + obj_offset);
	 }
      }
   }
   
   if (lp_stat) {
      printf ("\n======================= LP Solver =========================");
      printf ("\n");
      printf ("Number of times LP solver called:                 "
              "%i\n",lp_stat->lp_calls);
      printf ("Number of calls from feasibility pump:            "
              "%i\n",lp_stat->fp_lp_calls);
      printf ("Number of calls from strong branching:            "
              "%i\n",lp_stat->str_br_lp_calls);
      printf ("Number of solutions found by LP solve:            "
              "%i\n",lp_stat->lp_sols);
      printf ("Number of bounds changed by strong branching:     "
              "%i\n",lp_stat->str_br_bnd_changes);
      printf ("Number of nodes pruned by strong branching:       "
              "%i\n",lp_stat->str_br_nodes_pruned);
      printf ("Number of bounds changed by branching presolver:  "
              "%i\n",lp_stat->prep_bnd_changes);
      printf ("Number of nodes pruned by branching presolver:    "
              "%i\n",lp_stat->prep_nodes_pruned);
      
      if (output_mode < 1) {
	 
	 printf ("\n==================== Rounding =============================");
	 printf ("\n");
	 printf ("Number of rounding heuristic called:                  ");
	 printf("%i\n", lp_stat->rh_calls);
	 printf ("Number of solutions found by rounding:                ");
	 printf("%i\n", lp_stat->rh_num_sols);
	 printf ("Time spent in rounding heuristic:                     %.2f\n", 
		 tim->rh); 
	 
	 printf ("\n==================== Diving Search =======================");
	 printf ("\n");
	 printf ("Number of times diving search heuristic called:       ");
	 printf("%i\n", lp_stat->ds_calls);
	 int i;
	 printf ("Number of solutions found by diving search:           ");
	 printf("%i\n", lp_stat->ds_num_sols);
	 printf ("Time spent in diving search:                         %.2f\n", 
		 tim->ds); 
	 printf("td-");
	 for(i = 0; i < DIVING_HEURS_CNT; i++){
	   printf("t%i: %i\t", i,lp_stat->ds_type_calls[i]);
	 }      
	 printf("\n");
	 printf("sf-");
	 for(i = 0; i < DIVING_HEURS_CNT; i++){
	   printf("t%i: %i\t", i,lp_stat->ds_type_num_sols[i]);
	 }      
	 printf("\n");
	 printf("ts-");      
	 for(i = 0; i < DIVING_HEURS_CNT; i++){
	   printf("t%i: %f\t", i,tim->ds_type[i]);
	 }      
	 printf("\n");
	 printf ("\n==================== Feasibility Pump =====================");
	 printf ("\n");
	 printf ("Number of times feasibility pump called:              ");
	 printf("%i\n", lp_stat->fp_calls);
	 printf ("Number of solutions found by feasibility pump:        ");
	 printf("%i\n", lp_stat->fp_num_sols);
	 printf ("Time spent in feasibility pump:                       %.2f\n", 
		 tim->fp); 
	 
	 printf ("\n==================== Local Search =========================");
	 printf ("\n");
	 printf ("Number of times local search heuristic called:        ");
	 printf("%i\n", lp_stat->ls_calls);
	 printf ("Number of solutions found by local search:            ");
	 printf("%i\n", lp_stat->ls_num_sols);
	 printf ("Time spent in local search:                           %.2f\n", 
		tim->ls); 
	 
	 printf ("\n==================== Fix-and-Relax ========================");
	 printf ("\n");
	 printf ("Number of times fix-and-relax heuristic called:       ");
	 printf("%i\n", lp_stat->fr_calls);
	 printf ("Number of solutions found by fix-and-relax:           ");
	 printf("%i\n", lp_stat->fr_num_sols);
	 printf ("Time spent in fix-and-relax:                          %.2f\n", 
		 tim->fr); 
      
	 printf ("\n=========================== Cuts ==========================");
	 printf ("\n");
	 printf ("total cuts accepted:                   %d\n",
		 lp_stat->cuts_generated);
	 printf ("total cuts added to LPs:               %d\n",
		 lp_stat->cuts_added_to_lps);
	 printf ("total cuts deleted from LPs:           %d\n",
		 lp_stat->cuts_deleted_from_lps);
	 printf ("total gomory cuts generated:           %d\n",
		 lp_stat->gomory_cuts);
	 printf ("total knapsack cuts generated:         %d\n",
		 lp_stat->knapsack_cuts);
	 printf ("total oddhole cuts generated:          %d\n",
		 lp_stat->oddhole_cuts);
	 printf ("total clique cuts generated:           %d\n",
		 lp_stat->clique_cuts);
	 printf ("total probing cuts generated:          %d\n",
		 lp_stat->probing_cuts);
	 printf ("total mir cuts generated:              %d\n",
		 lp_stat->mir_cuts);
	 printf ("total twomir cuts generated:           %d\n",
		 lp_stat->twomir_cuts);
	 printf ("total flow and cover cuts generated:   %d\n",
		 lp_stat->flowcover_cuts);
	 printf ("total rounding cuts generated:         %d\n",
		 lp_stat->rounding_cuts);
	 printf ("total lift and project cuts generated: %d\n",
		 lp_stat->lift_and_project_cuts);
	 printf ("total landp cuts generated:            %d\n",
		 lp_stat->landp_cuts);
	 
	 printf ("\n");
	 
	 printf ("cuts removed because of bad coeffs:    %d\n",
		 lp_stat->num_poor_cuts);
	 printf ("cuts removed because of duplicacy:     %d\n",
		 lp_stat->num_duplicate_cuts);
	 printf ("insufficiently violated cuts:          %d\n",
		 lp_stat->num_unviolated_cuts);
	 
	 printf ("\n");
	 
	 printf ("cuts in root:                          %d\n",
		 lp_stat->cuts_root);
	 printf ("gomory cuts in root:                   %d\n",
		 lp_stat->gomory_cuts_root);
	 printf ("knapsack cuts in root:                 %d\n",
		 lp_stat->knapsack_cuts_root);
	 printf ("oddhole cuts in root:                  %d\n",
		 lp_stat->oddhole_cuts_root);
	 printf ("clique cuts in root:                   %d\n",
		 lp_stat->clique_cuts_root);
	 printf ("probing cuts in root:                  %d\n",
		 lp_stat->probing_cuts_root);
	 printf ("mir cuts in root:                      %d\n",
		 lp_stat->mir_cuts_root);
	 printf ("twomir cuts in root:                   %d\n",
		 lp_stat->twomir_cuts_root);
	 printf ("flow and cover cuts in root:           %d\n",
		 lp_stat->flowcover_cuts_root);
	 printf ("rounding cuts in root:                 %d\n",
		 lp_stat->rounding_cuts_root);
	 printf ("lift and project cuts in root:         %d\n",
		 lp_stat->lift_and_project_cuts_root);
	 printf ("landp cuts in root:                    %d\n",
		 lp_stat->landp_cuts_root);
	 
	 printf ("\n");
	 
	 printf ("time in cut generation: %.2f\n", tim->cuts);
	 printf ("time in gomory cuts in %d calls: %.2f\n", 
		 lp_stat->gomory_calls, tim->gomory_cuts);
	 printf ("time in knapsack cuts in %d calls: %.2f\n",
		 lp_stat->knapsack_calls, tim->knapsack_cuts);
	 printf ("time in oddhole cuts in %d calls: %.2f\n", 
		 lp_stat->oddhole_calls, tim->oddhole_cuts);
	 printf ("time in clique cuts in %d calls: %.2f\n", 
		 lp_stat->clique_calls, tim->clique_cuts);
	 printf ("time in probing cuts in %d calls: %.2f\n", 
		 lp_stat->probing_calls, tim->probing_cuts);
	 printf ("time in mir cuts in %d calls: %.2f\n", 
		 lp_stat->mir_calls, tim->mir_cuts);
	 printf ("time in twomir cuts in %d calls: %.2f\n", 
		 lp_stat->twomir_calls, tim->twomir_cuts);
	 printf ("time in flow and cover cuts in %d calls: %.2f\n",
		 lp_stat->flowcover_calls, tim->flowcover_cuts);
	 printf ("time in rounding cuts in %d calls: %.2f\n",
		 lp_stat->rounding_calls, tim->rounding_cuts);
	 printf ("time in lift and project cuts in %d calls: %.2f\n",
		 lp_stat->lift_and_project_calls, tim->lift_and_project_cuts);
	 printf ("time in landp cuts in %d calls: %.2f\n", 
		 lp_stat->landp_calls, tim->landp_cuts);
	 printf ("time in redsplit cuts in %d calls: %.2f\n", 
		 lp_stat->redsplit_calls, tim->redsplit_cuts);
	 printf ("time in checking quality and adding: %.2f\n", 
		 tim->dupes_and_bad_coeffs_in_cuts);
	 

      } else{
	 printf ("\n==================== Primal Heuristics ====================");	
	 printf ("\n");
	 printf ("%22s %10s %12s %12s\n","","Time","#Called", "#Solutions");
	 
	 printf ("%-22s %10.2f ", "Rounding I", tim->rh);
	 if (lp_stat->rh_calls > 0)
	    printf ("%12i %12i ",lp_stat->rh_calls, lp_stat->rh_num_sols);
	 else 
	    printf ("%12s %12s ","","");
	 printf ("\n");
	 
	 printf ("%-22s %10.2f ", "Rounding II", tim->sh);
	 if (lp_stat->sh_calls > 0)
	    printf ("%12i %12i ",lp_stat->sh_calls, lp_stat->sh_num_sols);
	 else 
	    printf ("%12s %12s ","","");
	 printf ("\n");
	 
	 printf ("%-22s %10.2f ", "Diving", tim->ds);
	 if (lp_stat->ds_calls > 0) {
	    printf ("%12i %12i ",lp_stat->ds_calls, lp_stat->ds_num_sols);	  
	    printf ("\n");	
	    for(int i = 0; i < DIVING_HEURS_CNT; i++){
	       switch(i){
		case FRAC_FIX_DIVING: 
		  printf ("%5s%-17s ", "","FracF_");
		  break;
		case FRAC_DIVING: 
		  printf ("%5s%-17s ", "","Frac_");
		  break;
		case VLENGTH_FIX_DIVING:
		  printf ("%5s%-17s ", "","VecLF_");
		  break;  
		case VLENGTH_DIVING:
		  printf ("%5s%-17s ", "","VecL_");
		  break;  
		case EUC_FIX_DIVING:
		  printf ("%5s%-17s ", "","EucF_");
		  break;  
		case EUC_DIVING:
		  printf ("%5s%-17s ", "","Euc_");
		  break;  
		case GUIDED_FIX_DIVING:
		  printf ("%5s%-17s ", "","GuidedF_");
		  break;  
		case GUIDED_DIVING:
		  printf ("%5s%-17s ", "","Guided_");
		  break;  
		case CROSSOVER_FIX_DIVING:
		  printf ("%5s%-17s ", "","COverF_");
		  break;  
		case CROSSOVER_DIVING:
		  printf ("%5s%-17s ", "","COver_");
		  break;  
		case RANK_FIX_DIVING:
		  printf ("%5s%-17s ", "","RankF_");
		  break;  
		case RANK_DIVING:
		  printf ("%5s%-17s ", "","Rank_");
		  break;  
		case COEFF_DIVING:
		  printf ("%5s%-17s ", "","Coeff_");
		  break;  
		case PC_DIVING:
		  printf ("%5s%-17s ", "","PseudoC_");
		  break;  
		default:
		  break;
	       }
	       printf("%10.2f ", tim->ds_type[i]);
	       if (lp_stat->ds_type_calls[i] > 0)
		  printf ("%12i %12i",lp_stat->ds_type_calls[i], 
			  lp_stat->ds_type_num_sols[i]);
	       //printf ("%12i %12i %12i",lp_stat->ds_type_calls[i], 
	       //lp_stat->ds_type_num_sols[i], lp_stat->ds_type_num_iter[i]);
	       printf ("\n");
	    }
	 } else {
	    printf ("\n");	
	 }	
	 
	 printf ("%-22s %10.2f ", "Feasibility Pump", tim->fp);
	 if (lp_stat->fp_calls > 0)
	    // printf ("%12i %12i %12i",lp_stat->fp_calls, lp_stat->fp_num_sols, lp_stat->fp_num_iter);
	    printf ("%12i %12i",lp_stat->fp_calls, lp_stat->fp_num_sols);
	 printf ("\n");	
	 
	 printf ("%-22s %10.2f ", "Local Search", tim->ls);
	 if (lp_stat->ls_calls > 0)
	    printf ("%12i %12i ",lp_stat->ls_calls, lp_stat->ls_num_sols);
	 printf ("\n");	
	 printf ("%-22s %10.2f ", "Restricted Search", tim->fr);
	 if (lp_stat->fr_calls > 0)
	    printf ("%12i %12i ",lp_stat->fr_calls, lp_stat->fr_num_sols);
	 printf ("\n");	
	 printf ("%-22s %10.2f ", "Rins Search", tim->rs);
	 if (lp_stat->rs_calls > 0)
	    printf ("%12i %12i ",lp_stat->rs_calls, lp_stat->rs_num_sols);
	 printf ("\n");	
	 printf ("%-22s %10.2f ", "Local Branching", tim->lb);
	 if (lp_stat->lb_calls > 0)
	    printf ("%12i %12i ",lp_stat->lb_calls, lp_stat->lb_num_sols);
	 
	 printf ("\n");	
	 printf ("\n=========================== Cuts ==========================");
	 printf ("\n");
	 printf ("Accepted:                         %d\n",
		 lp_stat->cuts_generated);
	 printf ("Added to LPs:                     %d\n",
		 lp_stat->cuts_added_to_lps);
	 printf ("Deleted from LPs:                 %d\n",
		 lp_stat->cuts_deleted_from_lps);
	 printf ("Removed because of bad coeffs:    %d\n",
		 lp_stat->num_poor_cuts);
	 printf ("Removed because of duplicacy:     %d\n",
		 lp_stat->num_duplicate_cuts);
	 printf ("Insufficiently violated:          %d\n",
		 lp_stat->num_unviolated_cuts);	
	 printf ("In root:                          %d\n",
		 lp_stat->cuts_root);
	 printf ("\n");	
	 
	 printf ("Time in cut generation:              %.2f\n", tim->cuts);	
	 printf ("Time in checking quality and adding: %.2f\n", 
		 tim->dupes_and_bad_coeffs_in_cuts);
	 
	 printf ("\n");	
	 printf ("%15s %7s %11s %11s %11s\n","","Time", "#Called", "In Root", "Total");
	 
	 printf ("%-15s %7.2f ","Gomory",tim->gomory_cuts); 
	 if(lp_stat->gomory_calls)
	    printf ("%11i %11i %11i ", lp_stat->gomory_calls, lp_stat->gomory_cuts_root, 
		    lp_stat->gomory_cuts);
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","Knapsack",tim->knapsack_cuts); 
	 if(lp_stat->knapsack_calls)
	    printf ("%11i %11i %11i ", lp_stat->knapsack_calls, 
		    lp_stat->knapsack_cuts_root, lp_stat->knapsack_cuts);		  
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","Clique",tim->clique_cuts); 
	 if(lp_stat->clique_calls)
	    printf ("%11i %11i %11i ", lp_stat->clique_calls, lp_stat->clique_cuts_root, 
		    lp_stat->clique_cuts);
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","Probing",tim->probing_cuts); 
	 if(lp_stat->probing_calls)
	    printf ("%11i %11i %11i ", lp_stat->probing_calls, lp_stat->probing_cuts_root, 
		    lp_stat->probing_cuts);
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","Flowcover",tim->flowcover_cuts); 
	 if(lp_stat->flowcover_calls)
	    printf ("%11i %11i %11i ", lp_stat->flowcover_calls, 
		    lp_stat->flowcover_cuts_root, lp_stat->flowcover_cuts);
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","Twomir",tim->twomir_cuts); 
	 if(lp_stat->twomir_calls)
	    printf ("%11i %11i %11i ", lp_stat->twomir_calls, lp_stat->twomir_cuts_root, 
		    lp_stat->twomir_cuts);
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","Oddhole",tim->oddhole_cuts); 
	 if(lp_stat->oddhole_calls)
	    printf ("%11i %11i %11i ", lp_stat->oddhole_calls, lp_stat->oddhole_cuts_root, 
		    lp_stat->oddhole_cuts);
	 printf ("\n");		
	 
	 
	 printf ("%-15s %7.2f ","Mir",tim->mir_cuts); 
	 if(lp_stat->mir_calls)
	    printf ("%11i %11i %11i ", lp_stat->mir_calls, lp_stat->mir_cuts_root, 
		    lp_stat->mir_cuts);
	 printf ("\n");		
	 
	 
	 printf ("%-15s %7.2f ","Rounding",tim->rounding_cuts); 
	 if(lp_stat->rounding_calls)
	    printf ("%11i %11i %11i ", lp_stat->rounding_calls, 
		    lp_stat->rounding_cuts_root, lp_stat->rounding_cuts);		  
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","LandP-I",tim->lift_and_project_cuts); 
	 if(lp_stat->lift_and_project_calls)
	    printf ("%11i %11i %11i ", lp_stat->lift_and_project_calls, 
		    lp_stat->lift_and_project_cuts_root, 
		  lp_stat->lift_and_project_cuts);
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","LandP-II",tim->landp_cuts); 
	 if(lp_stat->landp_calls)
	    printf ("%11i %11i %11i ", lp_stat->landp_calls, lp_stat->landp_cuts_root, 
		    lp_stat->landp_cuts);
	 printf ("\n");		
	 
	 printf ("%-15s %7.2f ","Redsplit",tim->redsplit_cuts); 
	 if(lp_stat->redsplit_calls)
	    printf ("%11i %11i %11i ", lp_stat->redsplit_calls, 
		    lp_stat->redsplit_cuts_root, lp_stat->redsplit_cuts);		  
	 printf ("\n");	
	 printf ("\n===========================================================");
      }
   }
   if (has_ub){
      gap = fabs(100*(ub-lb)/ub);
   }

   if (obj_sense == SYM_MAXIMIZE){
      if (gap > -1e-07 && gap < 0){
	 printf("\nCurrent Lower Bound:         %.10f", -ub + obj_offset);
	 printf("\nCurrent Upper Bound:         %.10f", -lb + obj_offset);
	 printf("\nGap Percentage:              %.10f\n", -gap);
      } else if (!has_ub) {
	 printf("\nCurrent Upper Bound:         %.10f\n", -lb + obj_offset);
      }
   }else{
      if (gap > 1e-07){
	 printf("\nCurrent Upper Bound:         %.10f", ub + obj_offset);
	 printf("\nCurrent Lower Bound:         %.10f", lb + obj_offset);
	 printf("\nGap Percentage:              %.3f\n", gap);
      } else if (!has_ub){
	 printf("\nCurrent Lower Bound:         %.10f\n", lb + obj_offset);
      }
   }
}
