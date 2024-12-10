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

#define COMPILE_FOR_LP

#ifdef _OPENMP
#include "omp.h"
#endif
#include <stdlib.h>
#include <math.h>
#include <string.h>

#include "sym_proccomm.h"
#include "sym_qsort.h"
#include "sym_lp.h"
#include "sym_messages.h"
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_types.h"
#include "sym_pack_cut.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains general LP functions.
\*===========================================================================*/

/*===========================================================================*\
 * This function receives the problem data (if we are running in parallel)   
 * and intitializes the data structures.                                     
\*===========================================================================*/

int lp_initialize(lp_prob *p, int master_tid)
{
#ifndef COMPILE_IN_LP
   int msgtag, bytes, r_bufid;
#endif
#if !defined(COMPILE_IN_TM) || !defined(COMPILE_IN_LP)
   int s_bufid;
#endif
   int i, j;
   row_data *rows;
   var_desc **vars;

#ifdef COMPILE_IN_LP

   p->master = master_tid;

#else

   /* set stdout to be line buffered */
   setvbuf(stdout, (char *)NULL, _IOLBF, 0);

   register_process();

   /*------------------------------------------------------------------------*\
    * Receive tid info; request and receive problem specific data
   \*------------------------------------------------------------------------*/
   r_bufid = receive_msg(ANYONE, MASTER_TID_INFO);
   bufinfo(r_bufid, &bytes, &msgtag, &p->tree_manager);
   receive_int_array(&p->master, 1);
   receive_int_array(&p->proc_index, 1);
   freebuf(r_bufid);

#endif

   p->lp_data = (LPdata *) calloc(1, sizeof(LPdata));
   p->lp_data->mip = (MIPdesc *) calloc(1, sizeof(MIPdesc));
   
#pragma omp critical (lp_solver)
   open_lp_solver(p->lp_data);

   (void) used_time(&p->tt);

#if !defined(COMPILE_IN_TM) || !defined(COMPILE_IN_LP)
   s_bufid = init_send(DataInPlace);
   send_msg(p->master, REQUEST_FOR_LP_DATA);
   freebuf(s_bufid);
   int termcode; 
   CALL_WRAPPER_FUNCTION( receive_lp_data_u(p) );
#endif
   
   if (p->par.tailoff_gap_backsteps > 0 ||
       p->par.tailoff_obj_backsteps > 1){
      i = MAX(5, MAX(p->par.tailoff_gap_backsteps, p->par.tailoff_obj_backsteps));
      p->obj_history = (double *) malloc((i + 1) * DSIZE);
      for (j = 0; j <= i; j++){
	 p->obj_history[j] = -DBL_MAX;
      }
   }
#ifndef COMPILE_IN_LP
   if (p->par.use_cg){
      r_bufid = receive_msg(p->tree_manager, LP__CG_TID_INFO);
      receive_int_array(&p->cut_gen, 1);
      freebuf(r_bufid);
   }
#endif
   p->lp_data->rows =
      (row_data *) malloc((p->base.cutnum + BB_BUNCH) * sizeof(row_data));
   rows = p->lp_data->rows;
   for (i = p->base.cutnum - 1; i >= 0; i--){
      ( rows[i].cut = (cut_data *) malloc(sizeof(cut_data)) )->coef = NULL;
   }

   if (p->base.varnum > 0){
      vars = p->lp_data->vars = (var_desc **)
	 malloc(p->base.varnum * sizeof(var_desc *));
      for (i = p->base.varnum - 1; i >= 0; i--){
	 vars[i] = (var_desc *) malloc( sizeof(var_desc) );
	 vars[i]->userind = p->base.userind[i];
	 vars[i]->colind = i;
      }
   }

   /* Just to make sure this array is sufficently big */
   p->lp_data->not_fixed = (int *) malloc(p->par.not_fixed_storage_size*ISIZE);
   p->lp_data->tmp.iv = (int *) malloc(p->par.not_fixed_storage_size* 2*ISIZE);
   p->lp_data->tmp.iv_size = 2*p->par.not_fixed_storage_size;
   p->lp_data->cgl = p->par.cgl;

#ifdef COMPILE_IN_CG
   if (!p->cgp){
      p->cgp = (cg_prob *) calloc(1, sizeof(cg_prob));
   }
   
   cg_initialize(p->cgp, p->master);
#endif

   return(FUNCTION_TERMINATED_NORMALLY);
}   

/*===========================================================================*/

/*===========================================================================*\
 * This function continues to dive down the current chain until told to stop
 * by the tree manager. 
\*===========================================================================*/

int process_chain(lp_prob *p)
{
   int termcode;
   
   p->comp_times.lp += used_time(&p->tt);
   /* Create the LP */
   if ((termcode = create_subproblem_u(p)) < 0){
      /* User had problems creating initial LP. Abandon node. */
      p->comp_times.lp_setup+= used_time(&p->tt);
      return(termcode);
   }
   p->comp_times.lp_setup += used_time(&p->tt);

   p->last_gap = 0.0;
   p->dive = CHECK_BEFORE_DIVE;

   if (p->has_ub && p->par.set_obj_upper_lim) {
      set_obj_upper_lim(p->lp_data, p->ub - p->par.granularity + 
            p->lp_data->lpetol);
   }
   
   if (p->colgen_strategy & COLGEN_REPRICING){
      if (p->par.verbosity > 1){
	 printf("****************************************************\n");
	 printf("* Now repricing NODE %i LEVEL %i\n",
		p->bc_index, p->bc_level);
	 printf("****************************************************\n\n");
      }
      termcode = repricing(p);
      free_node_dependent(p);
   }else{
      if (p->par.verbosity > 1){
	 printf("****************************************************\n");
	 printf("* Now processing NODE %i LEVEL %i (from TM)\n",
		p->bc_index, p->bc_level);
	 printf("****************************************************\n\n");
	 PRINT(p->par.verbosity, 4, ("Diving set to %i\n\n", p->dive));
      }
      termcode = fathom_branch(p);

#ifdef COMPILE_IN_LP
OPENMP_ATOMIC_UPDATE
      p->tm->stat.chains++;
#pragma omp critical (tree_update)
{
OPENMP_ATOMIC_UPDATE
      p->tm->active_node_num--;
      //This should be unnecessary, as it is also done in purge_pruned_nodes 
      p->tm->active_nodes[p->proc_index] = NULL;
}
      free_node_dependent(p);
#else
      /* send_lp_is_free()  calls  free_node_dependent() */
      send_lp_is_free(p);
#endif
   }
   p->lp_data->col_set_changed = TRUE;

   p->comp_times.lp += used_time(&p->tt);

   return(termcode);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function receives information for an active node, processes that     *
 * node and then decides which one of the children of that node should be    *
 * processed next. It then recursively processes the child until the branch  *
 * is pruned at point                                                        *
\*===========================================================================*/

int fathom_branch(lp_prob *p)
{
   LPdata *lp_data = p->lp_data;
   node_times *comp_times = &p->comp_times;
   char first_in_loop = TRUE;
   int iterd, termcode, feas_status; 
   int cuts = 0, no_more_cuts_count;
   int num_errors = 0;
   int cut_term = 0;
   double obj_before_cuts = 0;
   double timeleft = 0.0;
   int iterleft = 0;
   const int verbosity = p->par.verbosity;
   double now, then2, timeout2;
   int rs_mode_enabled = FALSE;
#ifdef COMPILE_IN_LP
   rs_mode_enabled = p->tm->par.rs_mode_enabled; 
   then2 = wall_clock(NULL);
   timeout2 = p->tm->par.status_interval;
#endif   
   check_ub(p);
   p->iter_num = p->node_iter_num = 0;
   
   // TODO: replace check_bounds with a better preprocessor
   termcode = LP_OPTIMAL; // just to initialize
   check_bounds(p, &termcode);
   if (termcode == LP_D_UNBOUNDED) {
      PRINT(verbosity, 1, ("Feasibility lost -- "));
      if (fathom(p, FALSE, FALSE)) {
         comp_times->communication += used_time(&p->tt);
         return(FUNCTION_TERMINATED_NORMALLY);
      }
   }

  
   /*------------------------------------------------------------------------*\
    * The main loop -- continue solving relaxations until no new cuts
    * are found
   \*------------------------------------------------------------------------*/

#ifdef COMPILE_IN_LP
   while (p->tm->termcode == TM_UNFINISHED){
#else
   while (TRUE){
#endif
      if (p->par.branch_on_cuts && p->slack_cut_num > 0){
	 switch (p->par.discard_slack_cuts){
	  case DISCARD_SLACKS_WHEN_STARTING_NEW_NODE:
	    if (p->iter_num != 0)
	       break;
	  case DISCARD_SLACKS_BEFORE_NEW_ITERATION:
	    free_cuts(p->slack_cuts, p->slack_cut_num);
	    p->slack_cut_num = 0;
	    break;
	 }
      }

#ifdef COMPILE_IN_LP
      
      //set time limit here      

      if (p->tm->par.time_limit >= 0.0 &&
	  (timeleft = p->tm->par.time_limit - wall_clock(NULL) + p->tm->start_time) <= 0.0) { 
         if (fathom(p, TRUE, TRUE)){  //send in true for interrupted node
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    return(FUNCTION_TERMINATED_ABNORMALLY);
	 }
      }
      
      if (timeleft > 0.0){
	 set_timelim(lp_data, timeleft);
      }


      // set itlim here if we are in restricted search heuristic

      if(rs_mode_enabled &&
	 (iterleft = p->tm->par.rs_lp_iter_limit - p->tm->lp_stat.lp_iter_num) <= 0) {
         if (fathom(p, TRUE, FALSE)){  //send in true for interrupted node
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    return(FUNCTION_TERMINATED_ABNORMALLY);
	 }
      }

      if (iterleft > 0){
	 set_itlim(lp_data, iterleft); 
      }      

#endif
      
      p->iter_num++;
      p->node_iter_num++;
      lp_data->lp_count++;
      
      PRINT(verbosity, 2,
	    ("\n\n**** Starting iteration %i ****\n\n", p->iter_num));

      p->bound_changes_in_iter = 0;

      if (!rs_mode_enabled && p->par.debug_lp){
	 char name[50] = "";
	 sprintf(name, "matrix.%i.%i", p->bc_index, p->iter_num);
	 write_lp(lp_data, name);
      }
      if ((p->iter_num < 2 && (p->par.should_warmstart_chain == FALSE || 
			       p->bc_level < 1))) {
         if (p->bc_index == 0) {
            PRINT(verbosity, 0, ("solving root lp relaxation\n"));
         }
         termcode = initial_lp_solve(lp_data, &iterd);	 
      } else {
	 termcode = dual_simplex(lp_data, &iterd);
      }
      if (p->bc_index < 1 && p->iter_num < 2) {
	 p->root_objval = lp_data->objval;
         if (p->par.should_reuse_lp == TRUE) {
           save_lp(lp_data);
         }
      }
      p->lp_stat.lp_calls++;
      p->lp_stat.lp_node_calls++;

#ifdef COMPILE_IN_LP
OPENMP_ATOMIC_UPDATE
      p->tm->lp_stat.lp_iter_num += iterd;
#endif

      p->lp_stat.lp_total_iter_num += iterd;

      if(iterd > p->lp_stat.lp_max_iter_num){
	 p->lp_stat.lp_max_iter_num = iterd;
      }
      
      /* Get relevant data */
      //get_dj_pi(lp_data);
      //get_slacks(lp_data);
      //get_x(lp_data);

      if(p->bc_level > 0 && p->node_iter_num < 2 && termcode == LP_OPTIMAL){
	 p->lp_stat.node_cuts_tried = 0;
	 p->lp_stat.node_cuts_forced = 0;
	 //update_solve_parameters(p);
	 update_cut_parameters(p);
      }else if(p->bc_level < 1){
	 p->lp_stat.node_cuts_tried = TRUE; 
	 if (p->node_iter_num) {
	    p->cgl_init_obj = lp_data->objval; 
	 }
      }
      
#if 1
      if(p->par.use_sos_branching && p->mip->opt_sol){
	 double *opt_sol = p->mip->opt_sol;
	 double ub, lb;
	 int is_feas = TRUE;
	 for(int i = 0; i < lp_data->n; i++){
	    get_lb(lp_data, i, &lb);
	    get_ub(lp_data, i, &ub);
	    if(opt_sol[i] < lb - lp_data->lpetol || opt_sol[i] > ub + lp_data->lpetol){
	       is_feas = FALSE;
	       break;
	    }
	 }
	 if(is_feas){
	    printf("bc_ind %i termcode %i\n", p->bc_index, termcode);
	 }
      }
#endif
      
      /* display the current solution */
      if (p->mip->obj_sense == SYM_MAXIMIZE){
         if (termcode == LP_OPTIMAL &&
	     ((p->bc_level < 1 && p->iter_num == 1) || verbosity > 2)) {
            PRINT(verbosity, 0, ("The LP value is: %.3f [%i,%i]\n\n",
                                   -lp_data->objval + p->mip->obj_offset,
                                   termcode, iterd));
         }

      }else{
         if (termcode == LP_OPTIMAL &&
	     ((p->bc_level < 1 && p->iter_num == 1) || verbosity > 2)) {
            PRINT(verbosity, 0, ("The LP value is: %.3f [%i,%i]\n\n",
                                   lp_data->objval+ p->mip->obj_offset,
                                   termcode, iterd));
         }
      }
      switch (termcode){
       case LP_D_INFEASIBLE: /* this is impossible (?) as of now */
	 return(ERROR__DUAL_INFEASIBLE);
       case LP_D_ITLIM:
       case LP_TIME_LIMIT:
	 /* now, we set time limit - solver returns the same termcode with itlim */
	 /* also, we might set iter limit if we are in search heuristics */
	 if (fathom(p, TRUE, FALSE)){  //send in true for interrupted node
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    return(FUNCTION_TERMINATED_ABNORMALLY);
	 }
       case LP_ABANDONED:
	 if (!rs_mode_enabled){
	    printf("####### Unexpected termcode: %i \n", termcode);
	 }
	 if (p->par.try_to_recover_from_error && (++num_errors == 1)){
	    /* Try to resolve it from scratch */
	    if (!rs_mode_enabled){
	       printf("####### Trying to recover by resolving from scratch...\n");
	    }
	    continue;
	 }else{
	    if (!rs_mode_enabled){   
	       char name[50] = "";
	       printf("####### Recovery failed. %s%s",
		      "LP solver is having numerical difficulties :(.\n",
		      "####### Dumping current LP to MPS file and exiting.\n\n");
	       sprintf(name, "matrix.%i.%i", p->bc_index, p->iter_num);
	       write_mps(lp_data, name);
	    }
	    return(ERROR__NUMERICAL_INSTABILITY);
	 }

       case LP_D_UNBOUNDED: /* the primal problem is infeasible */
       case LP_D_OBJLIM:
       case LP_OPTIMAL:
	 if (num_errors == 1 && !rs_mode_enabled){
	    printf("####### Recovery succeeded! Continuing with node...\n\n");
	    num_errors = 0;
	 }
	 if (termcode == LP_D_UNBOUNDED){
	    PRINT(verbosity, 1, ("Feasibility lost -- "));
#if 0
	    char name[50] = "";
	    sprintf(name, "matrix.%i.%i", p->bc_index, p->iter_num);
	    write_mps(lp_data, name);
#endif
	 }else if ((p->has_ub && lp_data->objval > p->ub - p->par.granularity +
		    p->lp_data->lpetol) || 
		   termcode == LP_D_OBJLIM){
	    PRINT(verbosity, 1, ("Terminating due to high cost -- "));
	 }else{ /* optimal and not too high cost */
#ifdef COMPILE_IN_LP
#ifdef DO_TESTS
            if (lp_data->objval < p->tm->lb - .001 && p->bc_index > 0){
               printf("#####Warning: lower bound corruption detected\n");
            }
#endif
	    p->tm->active_nodes[p->proc_index]->lower_bound = lp_data->objval;
            if (p->node_iter_num < 2 && p->bc_index > 0 && 
                  p->par.should_use_rel_br) {
               update_pcost(p);
            }
            if (cuts > 0) {
               p->lp_stat.cuts_added_to_lps += cuts;
            }
            if (p->node_iter_num > 0 && p->bc_level > 0) {
               if (cuts > 0) {
                  p->lp_stat.num_cuts_added_in_path += cuts;
               }
               if (p->lp_stat.avg_cuts_obj_impr_in_path > 0) {
                  p->lp_stat.avg_cuts_obj_impr_in_path = 
                     (p->lp_stat.avg_cuts_obj_impr_in_path *
                      (p->lp_stat.num_cut_iters_in_path-1) + p->lp_data->objval - 
                      obj_before_cuts)/p->lp_stat.num_cut_iters_in_path;
               }
            }

	    if(p->node_iter_num > 1){
	       p->lp_stat.end_objval = lp_data->objval;
	    }else{
	       p->lp_stat.end_objval = p->lp_stat.start_objval =
		  lp_data->objval;
	    }

            obj_before_cuts = lp_data->objval;
            comp_times->lp += used_time(&p->tt);
#endif
            break;
	 }
	 comp_times->lp += used_time(&p->tt);
	 if (fathom(p, (termcode != LP_D_UNBOUNDED), FALSE)){
	    comp_times->communication += used_time(&p->tt);
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    first_in_loop = FALSE;
	    comp_times->communication += used_time(&p->tt);
	    continue;
	 }
      }

      /* If come to here, the termcode must have been OPTIMAL and the
       * cost cannot be too high. */
      /* is_feasible_u() fills up lp_data->x, too!! */
      feas_status = is_feasible_u(p, FALSE, FALSE);
      if (feas_status == IP_FEASIBLE ||
	  (feas_status == IP_HEUR_FEASIBLE && p->par.find_first_feasible)){
	cuts = -1;
      }else{
	 /*------------------------------------------------------------------*\
	  * send the current solution to the cut generator, and also to the
	  * cut pool if we are either
	  *  - at the beginning of a chain (but not in the root in the
	  *         first phase)
	  *  - or this is the cut_pool_check_freq-th iteration.
	 \*------------------------------------------------------------------*/
	 cuts = 0;
	 no_more_cuts_count = 0;
	 if (p->cut_pool &&
	     ((first_in_loop && (p->bc_level>0 || p->phase==1)) ||
	      (p->iter_num % p->par.cut_pool_check_freq == 0)) ){
	    no_more_cuts_count += send_lp_solution_u(p, p->cut_pool);
	 }
	 if (p->cut_gen){
	    no_more_cuts_count += send_lp_solution_u(p, p->cut_gen);
	 }

	 if (verbosity > 4){
	    printf ("Now displaying the relaxed solution ...\n");
	    display_lp_solution_u(p, DISP_RELAXED_SOLUTION);
	 }

	 comp_times->lp += used_time(&p->tt);

	 tighten_bounds(p);

	 comp_times->fixing += used_time(&p->tt);

	 if (!first_in_loop){
	    cuts = check_row_effectiveness(p);
	 }

	 /*------------------------------------------------------------------*\
	  * receive the cuts from the cut generator and the cut pool
	 \*------------------------------------------------------------------*/

#ifdef USE_SYM_APPLICATION
	    if ((cut_term = receive_cuts(p, first_in_loop,
                        no_more_cuts_count)) >=0 ){
               cuts += cut_term;
            }else{
               return(ERROR__USER);
            }
#else
         if (!check_tailoff(p)) {
            if ((cut_term = receive_cuts(p, first_in_loop,
                        no_more_cuts_count)) >=0 ){
               cuts += cut_term;
            }else{
               return(ERROR__USER);
            }
         }
#endif
      }

      comp_times->lp += used_time(&p->tt);
      if (cuts < 0){ /* i.e. feasible solution is found */
	 if (fathom(p, TRUE, FALSE)){
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    first_in_loop = FALSE;
	    check_ub(p);
	    continue;
	 }
      }

      PRINT(verbosity, 2,
	    ("\nIn iteration %i, before calling branch()\n", p->iter_num));
      if (cuts == 0){
	 PRINT(verbosity, 2, ("... no cuts were added.\n"));
	 if (verbosity > 4){
	    printf("Now displaying final relaxed solution...\n\n");
	    display_lp_solution_u(p, DISP_FINAL_RELAXED_SOLUTION);
	 }
      }else{
	 PRINT(verbosity, 2, ("... %i violated cuts were added\n", cuts));
      }
      
      comp_times->lp += used_time(&p->tt);

      switch (cuts = branch(p, cuts)){

       case NEW_NODE:
#ifndef ROOT_NODE_ONLY
	 if (verbosity > 1){
	    printf("*************************************************\n");
	    printf("* Now processing NODE %i LEVEL %i\n",
		   p->bc_index, p->bc_level);
	    printf("*************************************************\n\n");
	 }
	 p->node_iter_num = 0;

#ifdef COMPILE_IN_LP
#pragma omp master
{
	 now = wall_clock(NULL);
	 if (now - then2 > timeout2){
	    if(verbosity >= -1 ){
	       print_tree_status(p->tm);
	    }
	    then2 = now;
	 }
 }
#endif
	 /*
         printf("node = %d\n", p->bc_index);
         printf("cut iters = %d\n", p->lp_stat.num_cut_iters_in_path);
         printf("cuts added = %d\n", p->lp_stat.num_cuts_added_in_path);
         printf("cut removed = %d\n", p->lp_stat.num_cuts_slacked_out_in_path);
         printf("cut obj impr = %f\n", p->lp_stat.avg_cuts_obj_impr_in_path);

         printf("strong br cands = %d\n", p->lp_stat.num_str_br_cands_in_path);
         printf("str br impr = %f\n", p->lp_stat.avg_br_obj_impr_in_path);

         printf("fp calls = %d\n", p->lp_stat.num_fp_calls_in_path);
         */
	 break;
#endif
       case FATHOMED_NODE:
	 comp_times->strong_branching += used_time(&p->tt);
	 return(FUNCTION_TERMINATED_NORMALLY);

       case BRANCHING_INF_NODE:
	 comp_times->strong_branching += used_time(&p->tt);
	 if (fathom(p, FALSE, FALSE)){
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    return(FUNCTION_TERMINATED_ABNORMALLY);
	 }

       case ERROR__NO_BRANCHING_CANDIDATE: /* Something went wrong */
	 return(ERROR__NO_BRANCHING_CANDIDATE);

       case FEAS_SOL_FOUND:
         PRINT(verbosity,2,("solution found before branching\n"));
	 if(p->par.find_first_feasible){
	   if(fathom(p, TRUE, FALSE)){  //send in true for interrupted node
	     return(FUNCTION_TERMINATED_NORMALLY);
	   }else{
	     return(FUNCTION_TERMINATED_ABNORMALLY);
	   }
	 }
       default: /* the return value is the number of cuts added */
	 if (verbosity > 2){
	    printf("Continue with this node.");
	    if (cuts > 0)
	       printf(" %i cuts added altogether in iteration %i\n",
		      cuts, p->iter_num);
            if (p->bound_changes_in_iter > 0) {
               printf(" %i bounds added altogether in iteration %i\n",
                     p->bound_changes_in_iter, p->iter_num);
            }
	    printf("\n\n");
	 }
#ifdef DO_TESTS
	 if (cuts == 0 && p->bound_changes_in_iter == 0){
	    printf("Error! Told not to branch, but there are no new cuts or ");
	    printf("bound changes!\n");
	    return(ERROR__NO_BRANCHING_CANDIDATE);
	 }
#endif
	 break;
      }
      comp_times->strong_branching += used_time(&p->tt);

      check_ub(p);
      first_in_loop = FALSE;      
      
#ifdef COMPILE_IN_LP
      char gap_limit_reached = FALSE;
      if(p->has_ub && p->tm->par.gap_limit >= 0.0 && 
	 (p->tm->samephase_candnum > 1 || p->tm->active_node_num > 1)){
	 //find_tree_lb(p->tm);	
	 if (d_gap(p->tm->ub, MIN(p->tm->lb, lp_data->objval), p->mip->obj_offset, p->mip->obj_sense) <= p->tm->par.gap_limit){
	    gap_limit_reached = TRUE;
	 }
      }
      //if(p->par.rs_mode_enabled)
      //	 printf("tm-lp-iter %i %i \n", p->tm->lp_stat.lp_iter_num, p->tm->par.rs_lp_iter_limit);
      if(p->par.rs_mode_enabled && p->tm->lp_stat.lp_iter_num > p->par.rs_lp_iter_limit){	 
	 gap_limit_reached = TRUE;
      }

      if (gap_limit_reached || 
	  (p->tm->par.time_limit >= 0.0 &&
	   wall_clock(NULL) - p->tm->start_time >= p->tm->par.time_limit)){
	 if (fathom(p, TRUE, ((gap_limit_reached) ? FALSE : TRUE))){
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    return(FUNCTION_TERMINATED_ABNORMALLY);
	 }
      } 
#else
      if (p->par.time_limit >= 0.0 &&
	  wall_clock(NULL) - p->start_time >= p->par.time_limit){
         if (fathom(p, TRUE, TRUE)){
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    return(FUNCTION_TERMINATED_ABNORMALLY);
	 }
      }
#endif
   }
   
   comp_times->lp += used_time(&p->tt);

   return(FUNCTION_TERMINATED_NORMALLY);
}

/*===========================================================================*/

/* fathom() returns true if it has really fathomed the node, false otherwise
   (i.e., if it had added few variables) */

int fathom(lp_prob *p, int primal_feasible, int time_limit_reached)
{
   LPdata *lp_data = p->lp_data;
   our_col_set *new_cols = NULL;
   int new_vars;
   int colgen = p->colgen_strategy & COLGEN__FATHOM;
   int termcode = p->lp_data->termcode;

#ifdef COMPILE_IN_LP
   if(p->branch_dir == 'L' && p->branch_var >= 0){
      p->br_inf_down[p->branch_var]++;
   }else{
      p->br_inf_up[p->branch_var]++;   
   }
#endif
   
   if (p->lp_data->nf_status == NF_CHECK_NOTHING){
      PRINT(p->par.verbosity, 1,
	    ("fathoming node (no more cols to check)\n\n"));
      if (primal_feasible){
         if (time_limit_reached) {
            send_node_desc(p, TIME_LIMIT);
         } else {
	    switch (termcode){
	       case LP_OPT_FEASIBLE:
	          send_node_desc(p, FEASIBLE_PRUNED);
	          break;
	       case LP_OPTIMAL:
	          send_node_desc(p, OVER_UB_PRUNED);
	          break;
	       case LP_D_ITLIM:
	          send_node_desc(p, ITERATION_LIMIT);
	          break;
	       case LP_TIME_LIMIT:
	          send_node_desc(p, TIME_LIMIT);
	          break;
	       default:
	          send_node_desc(p, OVER_UB_PRUNED);
	          break;
	    }
         }
      }else{
	 send_node_desc(p, INFEASIBLE_PRUNED);
      }
      return(TRUE);
   }
	 
   if (p->colgen_strategy & COLGEN_REPRICING)
      colgen = FATHOM__GENERATE_COLS__RESOLVE;

   switch (colgen){
    case FATHOM__DO_NOT_GENERATE_COLS__DISCARD:
      PRINT(p->par.verbosity, 1, ("Pruning node\n\n"));
      send_node_desc(p, termcode == LP_OPT_FEASIBLE ? FEASIBLE_PRUNED :
		     DISCARDED_NODE);
      return(TRUE);

    case FATHOM__DO_NOT_GENERATE_COLS__SEND:
      PRINT(p->par.verbosity, 1, ("Sending node for pricing\n\n"));
      send_node_desc(p, primal_feasible ? OVER_UB_HOLD_FOR_NEXT_PHASE :
		     INFEASIBLE_HOLD_FOR_NEXT_PHASE);
      return(TRUE);

    case FATHOM__GENERATE_COLS__RESOLVE:
      check_ub(p);
      /* Note that in case of COLGEN_REPRICING we must have UB. */
      if (! p->has_ub){
	 PRINT(p->par.verbosity, 1,
	       ("\nCan't generate cols before sending (no UB)\n"));
	 send_node_desc(p, primal_feasible ? OVER_UB_HOLD_FOR_NEXT_PHASE :
			INFEASIBLE_HOLD_FOR_NEXT_PHASE);
	 return(TRUE);
      }
      PRINT(p->par.verbosity, 1,
	    ("\nGenerating columns before fathoming/resolving\n"));
      new_cols = price_all_vars(p);
      p->comp_times.pricing += used_time(&p->tt);
      new_vars = new_cols->num_vars + new_cols->rel_ub + new_cols->rel_lb;
      if (new_cols->dual_feas == NOT_TDF){
	 /* Don't have total dual feasibility. The non-dual-feasible vars
	  * have already been added. Go back and resolve. */
	 PRINT(p->par.verbosity, 2,
	       ("%i variables added in price-out.\n", new_vars));
	 free_col_set(&new_cols);
	 return(FALSE);
      }
      /* Now we know that we have total dual feasibility */
      if ((p->has_ub && lp_data->objval > p->ub - p->par.granularity +
	   p->lp_data->lpetol) ||
	  termcode == LP_D_OBJLIM || termcode == LP_OPT_FEASIBLE){
	 /* fathomable */
	 if (termcode == LP_D_OBJLIM ||
	     (p->has_ub && lp_data->objval > p->ub - p->par.granularity +
	      p->lp_data->lpetol)){
	    PRINT(p->par.verbosity, 1,
		  ("Fathoming node (discovered tdf & high cost)\n\n"));
	 }else{
	    PRINT(p->par.verbosity, 1,
		  ("Fathoming node (discovered tdf & feasible)\n\n"));
	 }
	 send_node_desc(p, termcode == LP_OPT_FEASIBLE ? FEASIBLE_PRUNED :
			OVER_UB_PRUNED);
	 free_col_set(&new_cols);
	 return(TRUE);
      }
      /* If we ever arrive here then we must have tdf and the function
       * was called with a primal infeasible LP.
       *
       * Again, note that in case of COLGEN_REPRICING, since we do that
       * only in the root node, the lp relaxation MUST be primal feasible,
       *
       * If TDF_HAS_ALL, then whatever can be used to restore
       * primal feasibility is already in the matrix so don't bother
       * to figure out restorability, just return and resolve the problem
       * (if new_vars == 0 then even returning is unnecessary, the node
       * can be fathomed, nothing can restore feasibility).
       */
      if (new_cols->dual_feas == TDF_HAS_ALL){
	 if (new_vars == 0){
	    PRINT(p->par.verbosity, 1,
		  ("fathoming node (no more cols to check)\n\n"));
	    send_node_desc(p, INFEASIBLE_PRUNED);
	    free_col_set(&new_cols);
	    return(TRUE);
	 }else{
	    free_col_set(&new_cols);
	    return(FALSE);
	 }
      }
      /* Sigh. There were too many variables not fixable even though we have
       * proved tdf. new_cols contains a good many of the non-fixables, use
       * new_cols to start with in restore_lp_feasibility(). */
      if (! restore_lp_feasibility(p, new_cols)){
	 PRINT(p->par.verbosity, 1,
	       ("Fathoming node (discovered tdf & not restorable inf.)\n\n"));
	 send_node_desc(p, INFEASIBLE_PRUNED);
	 free_col_set(&new_cols);
	 return(TRUE);
      }
      /* So primal feasibility is restorable. Exactly one column has been
       * added (released or a new variable) to destroy the proof of
       * infeasibility */
      free_col_set(&new_cols);
      p->comp_times.pricing += used_time(&p->tt);
      return(FALSE);
   }

   return(TRUE); /* fake return */
}

/*****************************************************************************/
/*****************************************************************************/
/* NOTE: this version of repricing works ONLY for repricing in the root node */
/*****************************************************************************/
/*****************************************************************************/

int repricing(lp_prob *p)
{
   LPdata *lp_data = p->lp_data;
   node_times *comp_times = &p->comp_times;
   int iterd, termcode;
   int num_errors = 0;
   our_col_set *new_cols = NULL;
   int dual_feas, new_vars, cuts, no_more_cuts_count;
   int cut_term = 0;
   
   check_ub(p);
   p->iter_num = 0;
  
   /*------------------------------------------------------------------------*\
    * The main loop -- continue solving relaxations until TDF
   \*------------------------------------------------------------------------*/

   while (TRUE){
      p->iter_num++;

      PRINT(p->par.verbosity, 2,
	    ("\n\n**** Starting iteration %i ****\n\n", p->iter_num));

      termcode = dual_simplex(lp_data, &iterd);
      p->lp_stat.lp_calls++;
      /* Get relevant data */
      get_dj_pi(lp_data);
      get_slacks(lp_data);

      /* display the current solution */
      if (p->mip->obj_sense == SYM_MAXIMIZE){
	 PRINT(p->par.verbosity, 2, ("The LP value is: %.3f [%i,%i]\n\n",
				     -lp_data->objval + p->mip->obj_offset,
				     termcode, iterd));

      }else{
	 PRINT(p->par.verbosity, 2, ("The LP value is: %.3f [%i,%i]\n\n",
				     lp_data->objval+ p->mip->obj_offset,
				     termcode, iterd));
      }
      comp_times->lp += used_time(&p->tt);

      switch (termcode){
       case LP_D_ITLIM:      /* impossible, since itlim is set to infinity */
       case LP_D_INFEASIBLE: /* this is impossible (?) as of now */
       case LP_ABANDONED:
	 printf("######## Unexpected termcode: %i \n", termcode);
	 if (p->par.try_to_recover_from_error && (++num_errors == 1)){
	    /* Try to resolve it from scratch */
	    printf("######## Trying to recover by resolving from scratch...\n");
	    
	    continue;
	 }else{
	    char name[50] = "";
	    printf("######## Recovery failed. %s%s",
		   "LP solver is having numerical difficulties :(.\n",
		   "######## Dumping current LP to MPS file and exiting.\n\n");
	    sprintf(name, "matrix.%i.%i", p->bc_index, p->iter_num);
	    write_mps(lp_data, name);
	    return(ERROR__NUMERICAL_INSTABILITY);
	 }

       case LP_D_UNBOUNDED: /* the primal problem is infeasible */
       case LP_D_OBJLIM:
       case LP_OPTIMAL:
	 if (termcode == LP_D_UNBOUNDED){
	    PRINT(p->par.verbosity, 1, ("Feasibility lost -- "));
	 }else if ((p->has_ub && lp_data->objval > p->ub - p->par.granularity +
		    p->lp_data->lpetol)
		   || termcode == LP_D_OBJLIM){
	    PRINT(p->par.verbosity, 1, ("Terminating due to high cost -- "));
	 }else{ /* optimal and not too high cost */
	    break;
	 }
	 comp_times->lp += used_time(&p->tt);
	 if (fathom(p, (termcode != LP_D_UNBOUNDED), FALSE)){
	    comp_times->communication += used_time(&p->tt);
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    comp_times->communication += used_time(&p->tt);
	    continue;
	 }
      }

      /* If come to here, the termcode must have been OPTIMAL and the
       * cost cannot be too high. */
      /* is_feasible_u() fills up lp_data->x, too!! */
      if (is_feasible_u(p, FALSE, FALSE) == IP_FEASIBLE){
	 if (p->par.verbosity > 2){
	    printf ("Now displaying the feasible solution ...\n");
	    display_lp_solution_u(p, DISP_FEAS_SOLUTION);
	 }
	 cuts = -1;
      }else{

	 /*------------------------------------------------------------------*\
	  * send the current solution to the cut generator, and also to the
	  * cut pool if this is the 1st or cut_pool_check_freq-th iteration.
	 \*------------------------------------------------------------------*/

	 no_more_cuts_count = 0;
	 if (p->cut_pool &&
	     ((p->iter_num-1) % p->par.cut_pool_check_freq == 0) ){
	    no_more_cuts_count += send_lp_solution_u(p, p->cut_pool);
	 }
	 if (p->cut_gen){
	    no_more_cuts_count += send_lp_solution_u(p, p->cut_gen);
	 }

	 if (p->par.verbosity > 4){
	    printf ("Now displaying the relaxed solution ...\n");
	    display_lp_solution_u(p, DISP_RELAXED_SOLUTION);
	 }

	 comp_times->lp += used_time(&p->tt);

	 tighten_bounds(p);

	 comp_times->fixing += used_time(&p->tt);

	 cuts = 0;
	 if (p->cut_gen || p->cut_pool){
	    cuts = check_row_effectiveness(p);
	 }

	 /*------------------------------------------------------------------*\
	  * receive the cuts from the cut generator and the cut pool
	 \*------------------------------------------------------------------*/
         if ((cut_term = receive_cuts(p, TRUE, no_more_cuts_count)) >= 0){
            cuts += cut_term;
         }else{
            return(ERROR__USER);
         }
      }

      comp_times->lp += used_time(&p->tt);
      if (cuts < 0){ /* i.e. feasible solution is found */
	 if (fathom(p, TRUE, FALSE)){
	    comp_times->communication += used_time(&p->tt);
	    return(FUNCTION_TERMINATED_NORMALLY);
	 }else{
	    comp_times->communication += used_time(&p->tt);
	    check_ub(p);
	    continue;
	 }
      }

      if (cuts == 0){
	 PRINT(p->par.verbosity, 2,
	       ("\nIn iteration %i ... no cuts were added.\n", p->iter_num));
      }else{
	 /* Go back to top */
	 PRINT(p->par.verbosity, 2,
	       ("\nIn iteration %i ... %i violated cuts were added.\n",
		p->iter_num, cuts));
	 continue;
      }

      comp_times->lp += used_time(&p->tt);

      /* So no cuts were found. Price out everything */
      new_cols = price_all_vars(p);
      new_vars = new_cols->num_vars + new_cols->rel_ub + new_cols->rel_lb;
      dual_feas = new_cols->dual_feas;
      free_col_set(&new_cols);
      comp_times->pricing += used_time(&p->tt);
      if (dual_feas != NOT_TDF)
	 break;

      /* Don't have total dual feasibility. The non-dual-feasible vars
       * have already been added. Go back and resolve. */
      PRINT(p->par.verbosity, 2,
	    ("%i variables added in price-out.\n", new_vars));
   }

   /* Now we know that we have TDF, just send back the node */
   comp_times->lp += used_time(&p->tt);
   send_node_desc(p, REPRICED_NODE);
   comp_times->communication += used_time(&p->tt);

   return(FUNCTION_TERMINATED_NORMALLY);
}

/*===========================================================================*/

int bfind(int key, int *table, int size)
{
   int i = 0, k = size;
   int j = size >> 1;   /* the element to be probed */
   while ( i < k ){
      if (table[j] == key){
	 return(j);
      }else if (table[j] < key){
	 i = j + 1;
      }else{
	 k = j;
      }
      j = (i + k) >> 1;
   }
   return(j-1); /* key is not found and it is between the (j-1)st and j-th */
}

/*===========================================================================*/

int collect_nonzeros(lp_prob *p, double *x, int *tind, double *tx)
{
   var_desc **vars = p->lp_data->vars;
   int n = p->lp_data->n;
   int i, cnt = 0;
   double lpetol = p->lp_data->lpetol;

   if (p->par.is_userind_in_order != TRUE) {
      colind_sort_extra(p);
      for (i = 0; i < n; i++){
         if (x[i] > lpetol || x[i] < -lpetol){
            tind[cnt] = vars[i]->userind;
            tx[cnt++] = x[i];
         }
      }
      /* order indices and values according to indices */
      qsort_id(tind, tx, cnt);
   } else {
      for (i = 0; i < n; i++){
         if (x[i] > lpetol || x[i] < -lpetol){
            tind[cnt] = i;
            tx[cnt++] = x[i];
         }
      }
   }
   return(cnt);
}

/*===========================================================================*/

int collect_fractions(lp_prob *p, double *x, int *tind, double *tx)
{
   var_desc **vars = p->lp_data->vars;
   int n = p->lp_data->n;
   int i, cnt = 0;
   double lpetol = p->lp_data->lpetol, xi;

   colind_sort_extra(p);
   for (i = 0; i < n; i++){
      xi = x[i];
      if (xi - floor(xi) > lpetol && ceil(xi) - xi > lpetol){
	 tind[cnt] = vars[i]->userind;
	 tx[cnt++] = x[i];
      }
   }
   /* order indices and values according to indices */
   qsort_id(tind, tx, cnt);
   return(cnt);
}

/*===========================================================================*/

int collect_int_fractions(lp_prob *p, double *x, int *tind, double *tx, int *int_cnt)
{
   var_desc **vars = p->lp_data->vars;
   int n = p->lp_data->n;
   int i, cnt = 0, i_cnt = 0;
   double lpetol = p->lp_data->lpetol, xi;

   for (i = 0; i < n; i++){
      if (vars[i]->is_int){
	 i_cnt++;
	 xi = x[i];
	 if (xi - floor(xi) > lpetol && ceil(xi) - xi > lpetol){
	    tind[cnt] = vars[i]->userind;
	    tx[cnt++] = x[i];
	 }
      }
   }
   *int_cnt = i_cnt; 
   return(cnt);
}

/*===========================================================================*/

node_desc *create_explicit_node_desc(lp_prob *p)
{
   LPdata *lp_data = p->lp_data;
   int m = lp_data->m, n = lp_data->n;

   int bvarnum = p->base.varnum;
   var_desc **extravars = lp_data->vars + bvarnum;
   int extravarnum = n - bvarnum;

   int bcutnum = p->base.cutnum;
   row_data *rows = lp_data->rows;
   int extrarownum = m - bcutnum;
   int cutindsize;

   node_desc *desc = (node_desc *) calloc(1, sizeof(node_desc));

   /* Will need these anyway for basis */
   int *rstat = (int *) malloc(m * ISIZE);
   int *cstat = (int *) malloc(n * ISIZE);
   int *erstat = (extrarownum == 0) ? NULL : (int *) malloc(extrarownum*ISIZE);
   int *ecstat = (extravarnum == 0) ? NULL : (int *) malloc(extravarnum*ISIZE);

   int *ulist, *clist; /* this later uses tmp.i1 */
   int cutcnt, i, j;
#ifndef COMPILE_IN_LP
   int s_bufid, r_bufid;
#endif

   get_basis(lp_data, cstat, rstat);
   if (extrarownum > 0)
      memcpy(erstat, rstat + bcutnum, extrarownum * ISIZE);
   if (extravarnum > 0)
      memcpy(ecstat, cstat + bvarnum, extravarnum * ISIZE);

   /* To start with, send the non-indexed cuts (only those which will be
      saved) to the treemanager and ask for names */
   for (cutcnt = cutindsize = 0, i = bcutnum; i < m; i++){
      if ((rows[i].cut->branch & CUT_BRANCHED_ON) ||
	  !rows[i].free || (rows[i].free && rstat[i] != SLACK_BASIC)){
	 cutindsize++;
	 if (rows[i].cut->name < 0)
	    cutcnt++;
      }
   }
   if (cutcnt > 0){
#ifdef COMPILE_IN_LP
      row_data *tmp_rows = (row_data *) malloc(cutcnt*sizeof(row_data));
      
      for (j = 0, i = bcutnum; j < cutcnt; i++){
	 if (rows[i].cut->name < 0 &&
	     (!rows[i].free || (rows[i].free && rstat[i] != SLACK_BASIC)))
	    tmp_rows[j++] = rows[i];
      }
      unpack_cut_set(p->tm, 0, cutcnt, tmp_rows);
      FREE(tmp_rows);
#else
      s_bufid = init_send(DataInPlace);
      send_int_array(&cutcnt, 1);
      for (i = bcutnum; i < m; i++){
	 if (rows[i].cut->name < 0 &&
	     (!rows[i].free || (rows[i].free && rstat[i] != SLACK_BASIC)))
	    pack_cut(rows[i].cut);
      }
      send_msg(p->tree_manager, LP__CUT_NAMES_REQUESTED);
      freebuf(s_bufid);
#endif
   }

   /* create the uind list and the extravars basis description */
   desc->uind.type = EXPLICIT_LIST;
   desc->uind.added = 0;
   desc->uind.size = extravarnum;
   desc->basis.extravars.type = EXPLICIT_LIST;
   desc->basis.extravars.size = extravarnum;
   desc->basis.extravars.list = NULL;
   if (extravarnum > 0){
      desc->uind.list = ulist = (int *) malloc(extravarnum * ISIZE);
      desc->basis.extravars.stat = ecstat;
      for (i = extravarnum - 1; i >= 0; i--)
	 ulist[i] = extravars[i]->userind;
      if (lp_data->ordering == COLIND_ORDERED)
	 qsort_ii(ulist, ecstat, extravarnum);
   }else{
      desc->uind.list = NULL;
      desc->basis.extravars.stat = NULL;
   }
   /* create the basevars basis description */
   desc->basis.basevars.type = EXPLICIT_LIST;
   desc->basis.basevars.size = bvarnum;
   desc->basis.basevars.list = NULL;
   if (bvarnum)
      desc->basis.basevars.stat = cstat;
   else
      FREE(cstat);

   /* create the not_fixed list */
   desc->nf_status = lp_data->nf_status;
   if (desc->nf_status == NF_CHECK_AFTER_LAST ||
       desc->nf_status == NF_CHECK_UNTIL_LAST){
      desc->not_fixed.type = EXPLICIT_LIST;
      desc->not_fixed.added = 0;
      if ((desc->not_fixed.size = lp_data->not_fixed_num) > 0){
	 desc->not_fixed.list = (int *) malloc(desc->not_fixed.size * ISIZE);
	 memcpy(desc->not_fixed.list, lp_data->not_fixed,
		lp_data->not_fixed_num * ISIZE);
      }else{
	 desc->not_fixed.list = NULL;
      }
   }

#ifndef COMPILE_IN_LP
   /* At this point we will need the missing names */
   if (cutcnt > 0){
      static struct timeval tout = {15, 0};
      int *names = lp_data->tmp.i1; /* m */
      double start = wall_clock(NULL);
      do{
	 r_bufid = treceive_msg(p->tree_manager, LP__CUT_NAMES_SERVED, &tout);
	 if (! r_bufid){
	    if (pstat(p->tree_manager) != PROCESS_OK){
	       printf("TM has died -- LP exiting\n\n");
	       exit(-301);
	    }
	 }
      }while (! r_bufid);
      p->comp_times.idle_names += wall_clock(NULL) - start;
      receive_int_array(names, cutcnt);
      for (j = 0, i = bcutnum; j < cutcnt; i++){
	 if (rows[i].cut->name < 0 &&
	     (!rows[i].free || (rows[i].free && rstat[i] != SLACK_BASIC)))
	    rows[i].cut->name = names[j++];
      }
   }
#endif

   /* create the cutind list and the extrarows basis description */
   desc->cutind.type = EXPLICIT_LIST;
   desc->cutind.added = 0;
   desc->cutind.size = cutindsize;
   desc->basis.extrarows.type = EXPLICIT_LIST;
   desc->basis.extrarows.list = NULL;
   desc->basis.extrarows.size = cutindsize;
   if (cutindsize > 0){
      desc->cutind.list = clist = (int *) malloc(cutindsize * ISIZE);
      desc->basis.extrarows.stat = erstat;
      for (cutindsize = 0, i = bcutnum; i < m; i++){
	 if ((rows[i].cut->branch & CUT_BRANCHED_ON) ||
	     !rows[i].free || (rows[i].free && rstat[i] != SLACK_BASIC)){
	    clist[cutindsize] = rows[i].cut->name;
	    erstat[cutindsize++] = rstat[i];
	 }
      }
      qsort_ii(clist, erstat, cutindsize);
   }else{
      desc->cutind.list = NULL;
      desc->basis.extrarows.stat = NULL;
   }
   /* create the baserows basis description */
   desc->basis.baserows.type = EXPLICIT_LIST;
   desc->basis.baserows.size = bcutnum;
   desc->basis.baserows.list = NULL;
   if (bcutnum)
      desc->basis.baserows.stat = rstat;
   else
      FREE(rstat);

   /* Mark that there is a basis */
   desc->basis.basis_exists = TRUE;

   /* Add user description */
   add_to_desc_u(p, desc);

   return(desc);
}

/*===========================================================================*/

int check_tailoff(lp_prob *p)
{
   int gap_backsteps = p->par.tailoff_gap_backsteps;
   int obj_backsteps = p->par.tailoff_obj_backsteps;
   double *obj_hist = p->obj_history;
   double tailoff_obj_frac = p->par.tailoff_obj_frac;
   double tailoff_gap_frac = p->par.tailoff_gap_frac; 
  
   int i;
   double sum, ub;

   if(p->bc_index < 1){
      tailoff_gap_frac *= 1.0091;
      tailoff_obj_frac /= 7.333; 
   }else{
      tailoff_gap_frac *= 0.877;
      tailoff_obj_frac *= 1.133;
   }

   if((p->lp_data->m - p->mip->m)/(1.0*p->mip->m) < 0.2
#ifdef COMPILE_IN_LP
      && p->tm->stat.analyzed < 100
#endif
      ){
      //tailoff_gap_frac *= 1.0091;
      //tailoff_obj_frac /= 7.333; 
      gap_backsteps = 4;
      obj_backsteps = 5;
   }
   
   int maxsteps = MAX(gap_backsteps, obj_backsteps);
   
   //if(p->tm->stat.analyzed > 1000 && p->node_iter_num > 1) return TRUE;
   
   p->has_tailoff = TRUE;
   if (gap_backsteps >= 1 || obj_backsteps >= 2) {
      
      /* shift the data in obj_hist by one to the right and insert the
	 most recent objval to be the 0th */
      for (i = MIN(p->node_iter_num-1, maxsteps) - 1; i >= 0; i--) {
	 obj_hist[i+1] = obj_hist[i];
      }
      obj_hist[0] = p->lp_data->objval;
      
      if (p->bc_index == 0) {

	 /*
          * root policy: generate cuts for min_root_cut_rounds and then stop.
	  * if obj value doesnt improve in last
          * tailoff_max_no_impr_iters_root, then stop.
          */
	 
	 //tailoff_obj_frac /= 2;  
	 double obj_gap = 0.0;
	 
	 if(obj_hist[0] >= obj_hist[1] + p->lp_data->lpetol){
	    obj_gap = fabs(obj_hist[1]/obj_hist[0] - 1.0);
	 }
	 
	 int weighted_iter = p->lp_stat.lp_total_iter_num/(p->iter_num + 1);
	 if(p->mip->nz > 2.5e4){
	    weighted_iter = (int) ((weighted_iter * p->mip->nz) / 2.5e4);
	 }

         if (obj_gap <= 1e-5 || (obj_gap <= 1e-4 && weighted_iter >= 1e4)){
            p->obj_no_impr_iters++;
         } else {
	    if(p->obj_no_impr_iters > 0){
	       p->obj_no_impr_iters--;
	    }
	 }
	 //if(p->iter_num > 1 && p->par.verbosity > -1)
	    //printf("w-iter - obj_gap - no_iter : %i %f %i\n", weighted_iter, obj_gap, p->obj_no_impr_iters);
	 
	 if(weighted_iter <= 400){
	    if (p->obj_no_impr_iters > 
		p->par.tailoff_max_no_iterative_impr_iters_root) {
	       for(i = 7; i >=0; --i){
		  if(weighted_iter >= 50*i &&
		     p->obj_no_impr_iters >= (9-i)){
		     p->has_tailoff = TRUE;
		     return (TRUE);
		  }
	       }
	    }

	    if (p->node_iter_num >= p->par.min_root_cut_rounds) {
	       p->has_tailoff = TRUE;
	       return (TRUE);
	    }else{
	       p->has_tailoff = FALSE;
	       return (FALSE);	       
	    }
	 }

	 if(weighted_iter >= 1e3){
	    if (p->obj_no_impr_iters >=
		p->par.tailoff_max_no_iterative_impr_iters_root) {
	       p->has_tailoff = TRUE;
	       return (TRUE);
	    }
	 }
	 
	 if (p->node_iter_num >= p->par.min_root_cut_rounds) {
	    p->has_tailoff = TRUE;
	    return (TRUE);
	 }
      }

      /* if there is an upper bound and we want gap based tailoff:
	 tailoff_gap is false if the average of the consecutive gap ratios is
	 less than gap_frac */
      if (p->node_iter_num>gap_backsteps && p->has_ub && gap_backsteps > 0) {
	 ub = p->ub;
	 for (i = 1, sum = 0; i <= gap_backsteps; i++) {
	    sum += (ub - obj_hist[i-1]) / (ub - obj_hist[i]);
	 }
	 //printf("tailoff-gap: %f %f\n", sum/gap_backsteps, tailoff_gap_frac);
	 if (sum / gap_backsteps > tailoff_gap_frac) {
	    PRINT(p->par.verbosity, 3, ("Branching because of tailoff in gap!\n"));
	    return(TRUE); /* there is tailoff */
	 }	 
      }

      /* if we want objective value based tailoff:
	 tailoff_obj is true if the average of the objective difference
	 ratios is smaller than par.tailoff_obj_frac */
      if (p->node_iter_num>obj_backsteps){
	 for (i = 2, sum = 0; i <= obj_backsteps; i++){
	    if (obj_hist[i-1] - obj_hist[i] > p->lp_data->lpetol){
	       sum += (obj_hist[i-2]-obj_hist[i-1]) / (obj_hist[i-1]-obj_hist[i]);
	    }else if (obj_hist[i-2] - obj_hist[i-1] > p->lp_data->lpetol){
	       sum += obj_backsteps;
	    }
	 }
	 //printf("tailoff-obj-gap: %f %f\n", sum/(obj_backsteps-1), tailoff_obj_frac);	 
	 double init_obj = obj_hist[MIN(p->node_iter_num-1, maxsteps)];
	 double prog = 10*p->par.tailoff_absolute; 
	 if(init_obj > p->lp_data->lpetol || init_obj < -p->lp_data->lpetol){
	    prog = (obj_hist[0] - init_obj)/(fabs(init_obj));
	 }

	 if (sum / (obj_backsteps - 1) < tailoff_obj_frac && prog < 5*p->par.tailoff_absolute){
	    PRINT(p->par.verbosity, 3, ("Branching because of tailoff in "
					"objective function!\n"));
	    PRINT(p->par.verbosity, 3, ("sum/n = %f, tailoff_obj_frac = %f\n",sum /
					(obj_backsteps - 1) , tailoff_obj_frac));
	    return(TRUE); /* there is tailoff */
	 }
      }

      /* Another check. All other checks seem to show that there is no
       * tailoff yet. 
       */
      if (p->bc_level > 0 && ((p->node_iter_num > 1 && fabs(obj_hist[0]) > p->lp_data->lpetol) || p->node_iter_num > maxsteps) && 
	  (obj_hist[0] - obj_hist[1] < p->par.tailoff_absolute)){
	 PRINT(p->par.verbosity, 3, ("Branching because of tailoff in "
				     "value of objective function!\n"));
	 return(TRUE);
      }

      //if(p->bc_level > 0 && p->node_iter_num > maxsteps && init_obj > p->lp_data->lpetol &&
      // (obj_hist[0] - init_obj)/(fabs(init_obj)) < 5*p->par.tailoff_absolute){
      // PRINT(p->par.verbosity, 3, ("Branching because of tailoff in "
      //			     "value of objective function II!\n"));
      // return(TRUE);	 
      //}      
      //printf("tailoff-absolute: %f %f\n", obj_hist[0] - obj_hist[1], p->par.tailoff_absolute);
   } else {
      /* Both gap_backsteps and obj_backsteps are too small to procede with
         check_tailoff. The user asks for tailoff (since we came to this
	 function) yet doesn't want to check any kind of tailoff (since this
	 condition is true). Report no tailoff. */
      p->has_tailoff=FALSE;
      return(FALSE); /* no tailoff */
   }

   p->has_tailoff=FALSE;
   return(FALSE); /* gone thru everything ==> no tailoff */
}


/*===========================================================================*/

void lp_exit(lp_prob *p)
{
   int s_bufid;

   s_bufid = init_send(DataInPlace);
   send_msg(p->tree_manager, SOMETHING_DIED);
   freebuf(s_bufid);
   comm_exit();
   exit(-1);
}

/*===========================================================================*/

void lp_close(lp_prob *p)
{
#ifndef COMPILE_IN_LP
   int s_bufid;
   
   /* Send back the timing data for the whole algorithm */
   s_bufid = init_send(DataInPlace);
   send_char_array((char *)&(p->comp_times), sizeof(node_times));
   send_char_array((char *)&(p->lp_stat), sizeof(lp_stat_desc));
   send_msg(p->tree_manager, LP__TIMING);
   freebuf(s_bufid);
#else
#pragma omp critical (timing_update)
{
   int i;
   p->tm->comp_times.communication    += p->comp_times.communication;
   p->tm->comp_times.lp               += p->comp_times.lp;
   p->tm->comp_times.lp_setup         += p->comp_times.lp_setup;
   p->tm->comp_times.separation       += p->comp_times.separation;
   p->tm->comp_times.fixing           += p->comp_times.fixing;
   p->tm->comp_times.pricing          += p->comp_times.pricing;
   p->tm->comp_times.strong_branching += p->comp_times.strong_branching;
   p->tm->comp_times.fp               += p->comp_times.fp;
   p->tm->comp_times.rh               += p->comp_times.rh;
   p->tm->comp_times.sh               += p->comp_times.sh;
   p->tm->comp_times.ls               += p->comp_times.ls;
   p->tm->comp_times.ds               += p->comp_times.ds;
   p->tm->comp_times.fr               += p->comp_times.fr;
   p->tm->comp_times.lb               += p->comp_times.lb;
   p->tm->comp_times.rs               += p->comp_times.rs;
   p->tm->comp_times.primal_heur      += p->comp_times.primal_heur;

   for(i = 0; i <  DIVING_HEURS_CNT; i++){
     p->tm->comp_times.ds_type[i] += p->comp_times.ds_type[i];
   }  

   p->tm->comp_times.cuts             += p->comp_times.cuts;
   p->tm->comp_times.gomory_cuts      += p->comp_times.gomory_cuts;
   p->tm->comp_times.knapsack_cuts    += p->comp_times.knapsack_cuts;
   p->tm->comp_times.oddhole_cuts     += p->comp_times.oddhole_cuts;
   p->tm->comp_times.clique_cuts      += p->comp_times.clique_cuts;
   p->tm->comp_times.probing_cuts     += p->comp_times.probing_cuts;
   p->tm->comp_times.mir_cuts         += p->comp_times.mir_cuts;
   p->tm->comp_times.twomir_cuts      += p->comp_times.twomir_cuts;
   p->tm->comp_times.rounding_cuts    += p->comp_times.rounding_cuts;
   p->tm->comp_times.landp_cuts       += p->comp_times.landp_cuts;
   p->tm->comp_times.flowcover_cuts   += p->comp_times.flowcover_cuts;
   p->tm->comp_times.lift_and_project_cuts += 
      p->comp_times.lift_and_project_cuts;
   p->tm->comp_times.redsplit_cuts += p->comp_times.redsplit_cuts;
   p->tm->comp_times.dupes_and_bad_coeffs_in_cuts += 
      p->comp_times.dupes_and_bad_coeffs_in_cuts;

   p->tm->lp_stat.lp_calls                += p->lp_stat.lp_calls;
   p->tm->lp_stat.lp_node_calls           += p->lp_stat.lp_node_calls;
   p->tm->lp_stat.str_br_lp_calls         += p->lp_stat.str_br_lp_calls;
   p->tm->lp_stat.lp_sols                 += p->lp_stat.lp_sols;
   p->tm->lp_stat.ip_sols                 += p->lp_stat.ip_sols;
   p->tm->lp_stat.str_br_bnd_changes      += p->lp_stat.str_br_bnd_changes;
   p->tm->lp_stat.str_br_nodes_pruned     += p->lp_stat.str_br_nodes_pruned;
   p->tm->lp_stat.prep_bnd_changes        += p->lp_stat.prep_bnd_changes; 
   p->tm->lp_stat.prep_nodes_pruned       += p->lp_stat.prep_nodes_pruned;
   p->tm->lp_stat.lp_iter_num             += p->lp_stat.lp_iter_num;
   
   p->tm->lp_stat.cuts_generated          += p->lp_stat.cuts_generated;
   p->tm->lp_stat.gomory_cuts             += p->lp_stat.gomory_cuts;
   p->tm->lp_stat.knapsack_cuts           += p->lp_stat.knapsack_cuts;
   p->tm->lp_stat.oddhole_cuts            += p->lp_stat.oddhole_cuts;
   p->tm->lp_stat.clique_cuts             += p->lp_stat.clique_cuts;
   p->tm->lp_stat.probing_cuts            += p->lp_stat.probing_cuts;
   p->tm->lp_stat.mir_cuts                += p->lp_stat.mir_cuts;
   p->tm->lp_stat.twomir_cuts             += p->lp_stat.twomir_cuts;
   p->tm->lp_stat.rounding_cuts           += p->lp_stat.rounding_cuts;
   p->tm->lp_stat.landp_cuts              += p->lp_stat.landp_cuts;
   p->tm->lp_stat.flowcover_cuts          += p->lp_stat.flowcover_cuts;
   p->tm->lp_stat.lift_and_project_cuts   += p->lp_stat.lift_and_project_cuts;
   p->tm->lp_stat.redsplit_cuts           += p->lp_stat.redsplit_cuts;

   p->tm->lp_stat.cuts_root               += p->lp_stat.cuts_root;
   p->tm->lp_stat.gomory_cuts_root        += p->lp_stat.gomory_cuts_root;
   p->tm->lp_stat.knapsack_cuts_root      += p->lp_stat.knapsack_cuts_root;
   p->tm->lp_stat.oddhole_cuts_root       += p->lp_stat.oddhole_cuts_root;
   p->tm->lp_stat.clique_cuts_root        += p->lp_stat.clique_cuts_root;
   p->tm->lp_stat.probing_cuts_root       += p->lp_stat.probing_cuts_root;
   p->tm->lp_stat.mir_cuts_root           += p->lp_stat.mir_cuts_root;
   p->tm->lp_stat.twomir_cuts_root        += p->lp_stat.twomir_cuts_root;
   p->tm->lp_stat.rounding_cuts_root      += p->lp_stat.rounding_cuts_root;
   p->tm->lp_stat.landp_cuts_root         += p->lp_stat.landp_cuts_root;
   p->tm->lp_stat.flowcover_cuts_root     += p->lp_stat.flowcover_cuts_root;
   p->tm->lp_stat.lift_and_project_cuts_root += 
      p->lp_stat.lift_and_project_cuts_root;
   p->tm->lp_stat.redsplit_cuts_root += 
      p->lp_stat.redsplit_cuts_root;

   p->tm->lp_stat.num_poor_cuts           += p->lp_stat.num_poor_cuts;
   p->tm->lp_stat.num_duplicate_cuts      += p->lp_stat.num_duplicate_cuts;
   p->tm->lp_stat.num_unviolated_cuts     += p->lp_stat.num_unviolated_cuts;
   p->tm->lp_stat.cuts_deleted_from_lps   += p->lp_stat.cuts_deleted_from_lps;
   p->tm->lp_stat.cuts_added_to_lps       += p->lp_stat.cuts_added_to_lps;

   p->tm->lp_stat.gomory_calls            += p->lp_stat.gomory_calls;
   p->tm->lp_stat.knapsack_calls          += p->lp_stat.knapsack_calls;
   p->tm->lp_stat.oddhole_calls           += p->lp_stat.oddhole_calls;
   p->tm->lp_stat.clique_calls            += p->lp_stat.clique_calls;
   p->tm->lp_stat.probing_calls           += p->lp_stat.probing_calls;
   p->tm->lp_stat.mir_calls               += p->lp_stat.mir_calls;
   p->tm->lp_stat.twomir_calls            += p->lp_stat.twomir_calls;
   p->tm->lp_stat.rounding_calls          += p->lp_stat.rounding_calls;
   p->tm->lp_stat.landp_calls             += p->lp_stat.landp_calls;
   p->tm->lp_stat.flowcover_calls         += p->lp_stat.flowcover_calls;
   p->tm->lp_stat.lift_and_project_calls  += p->lp_stat.lift_and_project_calls;
   p->tm->lp_stat.redsplit_calls          += p->lp_stat.redsplit_calls;

   p->tm->lp_stat.fp_calls                += p->lp_stat.fp_calls;
   p->tm->lp_stat.fp_lp_calls             += p->lp_stat.fp_lp_calls;
   p->tm->lp_stat.fp_num_sols             += p->lp_stat.fp_num_sols;
   p->tm->lp_stat.fp_num_iter             += p->lp_stat.fp_num_iter;
   p->tm->lp_stat.fp_last_call_ind         = p->lp_stat.fp_last_call_ind;

   p->tm->lp_stat.rh_calls                += p->lp_stat.rh_calls;
   p->tm->lp_stat.rh_num_sols             += p->lp_stat.rh_num_sols;
   p->tm->lp_stat.rh_last_call_ind         = p->lp_stat.rh_last_call_ind;

   p->tm->lp_stat.sh_calls                += p->lp_stat.sh_calls;
   p->tm->lp_stat.sh_num_sols             += p->lp_stat.sh_num_sols;
   p->tm->lp_stat.sh_last_call_ind         = p->lp_stat.sh_last_call_ind;

   p->tm->lp_stat.ls_calls                += p->lp_stat.ls_calls;
   p->tm->lp_stat.ls_num_sols             += p->lp_stat.ls_num_sols;
   p->tm->lp_stat.ls_last_call_ind         = p->lp_stat.ls_last_call_ind;

   p->tm->lp_stat.ds_calls                += p->lp_stat.ds_calls;
   p->tm->lp_stat.ds_num_sols             += p->lp_stat.ds_num_sols;
   p->tm->lp_stat.ds_num_iter             += p->lp_stat.ds_num_iter;
   p->tm->lp_stat.ds_last_call_ind         = p->lp_stat.ds_last_call_ind;

   p->tm->lp_stat.fr_calls                += p->lp_stat.fr_calls;
   p->tm->lp_stat.fr_num_sols             += p->lp_stat.fr_num_sols;
   p->tm->lp_stat.fr_last_call_ind         = p->lp_stat.fr_last_call_ind;
   p->tm->lp_stat.fr_analyzed_nodes       += p->lp_stat.fr_analyzed_nodes; 
   p->tm->lp_stat.fr_last_sol_call         = p->lp_stat.fr_last_sol_call; 

   p->tm->lp_stat.rs_calls                += p->lp_stat.rs_calls;
   p->tm->lp_stat.rs_num_sols             += p->lp_stat.rs_num_sols;
   p->tm->lp_stat.rs_last_call_ind         = p->lp_stat.rs_last_call_ind;
   p->tm->lp_stat.rs_analyzed_nodes       += p->lp_stat.rs_analyzed_nodes; 
   p->tm->lp_stat.rs_last_sol_call         = p->lp_stat.rs_last_sol_call; 

   p->tm->lp_stat.lb_calls                += p->lp_stat.lb_calls;
   p->tm->lp_stat.lb_num_sols             += p->lp_stat.lb_num_sols;
   p->tm->lp_stat.lb_last_call_ind         = p->lp_stat.lb_last_call_ind;
   p->tm->lp_stat.lb_analyzed_nodes       += p->lp_stat.lb_analyzed_nodes; 
   p->tm->lp_stat.lb_last_sol_call         = p->lp_stat.lb_last_sol_call;
   
   for(i = 0; i <  DIVING_HEURS_CNT; i++){
     p->tm->lp_stat.ds_type_calls[i] += p->lp_stat.ds_type_calls[i];
     p->tm->lp_stat.ds_type_num_sols[i] += p->lp_stat.ds_type_num_sols[i];
     p->tm->lp_stat.ds_type_num_iter[i] += p->lp_stat.ds_type_num_iter[i];     
   }
 }
#endif
#ifdef COMPILE_IN_CG
 cg_close(p->cgp);
#endif
#ifndef COMPILE_IN_TM
 free_lp(p);
#endif
}

/*===========================================================================*/
/*
 * save the changes in bounds that occurred while processing the current node
 * into current-node's node_desc. These changes are available by comparing
 * vars[i]->lb and vars[i]->new_lb etc. After saving the changes, vars[i]->lb,
 * vars[i]->ub are changed to new_lb and new_ub so that the same changes are
 * not saved in the child-node's desc.
 */
int add_bound_changes_to_desc(node_desc *desc, lp_prob *p)
{
#ifdef COMPILE_IN_LP
   LPdata                *lp_data = p->lp_data; 
   var_desc             **vars = lp_data->vars;
   int                    i, num_bnd_changes, cnt;
   bounds_change_desc    *bnd_change;
   int                   *index;
   char                  *lbub;
   double                *value;

   num_bnd_changes = 0;
   for (i=0;i<lp_data->n;i++) {
      if (vars[i]->new_lb>vars[i]->lb) {
         num_bnd_changes++;
      }
      if (vars[i]->new_ub<vars[i]->ub) {
         num_bnd_changes++;
      }
   }
   if (num_bnd_changes>0) {
      bnd_change = desc->bnd_change = (bounds_change_desc *) 
         calloc (1, sizeof(bounds_change_desc));
      bnd_change->num_changes = num_bnd_changes;
      index = bnd_change->index = (int *)malloc(num_bnd_changes*ISIZE);
      lbub  = bnd_change->lbub = (char *)malloc(num_bnd_changes*CSIZE);
      value = bnd_change->value = (double *)malloc(num_bnd_changes*DSIZE);
      cnt = 0;
      for (i=0;i<lp_data->n;i++) {
         if (vars[i]->new_lb>vars[i]->lb) {
            index[cnt] = vars[i]->userind;
            lbub[cnt] = 'L';
            value[cnt] = vars[i]->new_lb;
            cnt++;
            vars[i]->lb = vars[i]->new_lb;
         }
         if (vars[i]->new_ub<vars[i]->ub) {
            index[cnt] = vars[i]->userind;
            lbub[cnt] = 'U';
            value[cnt] = vars[i]->new_ub;
            cnt++;
            vars[i]->ub = vars[i]->new_ub;
         }
      }
   } else {
      if (desc->bnd_change) {
         FREE(desc->bnd_change->index);
         FREE(desc->bnd_change->lbub);
         FREE(desc->bnd_change->value);
         FREE(desc->bnd_change);
      }
      desc->bnd_change = NULL;
   }
#endif

   return 0;
}

/*===========================================================================*/
int str_br_bound_changes(lp_prob *p, int num_bnd_changes, double *bnd_val, 
      int *bnd_ind, char *bnd_sense)
{
#ifdef COMPILE_IN_LP
   bounds_change_desc    *bnd_change;
   int                   i, j;
   var_desc              **vars = p->lp_data->vars;
   int                   *index;
   double                *value;
   char                  *lbub;

   if (num_bnd_changes<1) {
      return 0;
   }
   if (p->tm->active_nodes[p->proc_index]->desc.bnd_change == NULL) {
      bnd_change = (bounds_change_desc *)calloc(1, sizeof(bounds_change_desc));
      index = bnd_change->index = (int *)malloc(num_bnd_changes*ISIZE);
      lbub = bnd_change->lbub = (char *)malloc(num_bnd_changes*CSIZE);
      value = bnd_change->value = (double *)malloc(num_bnd_changes*DSIZE);
      bnd_change->num_changes = num_bnd_changes;
      j = 0;
   } else {
      bnd_change = p->tm->active_nodes[p->proc_index]->desc.bnd_change;
      j = bnd_change->num_changes;
      bnd_change->num_changes += num_bnd_changes;
      index = bnd_change->index = (int *)realloc(bnd_change->index, 
            bnd_change->num_changes*ISIZE);
      lbub = bnd_change->lbub = (char *)realloc(bnd_change->lbub,
            bnd_change->num_changes*CSIZE);
      value = bnd_change->value = (double *)realloc(bnd_change->value,
            bnd_change->num_changes*DSIZE);
   }
   for (i = 0; i<num_bnd_changes; i++) {
      index[i+j] = vars[bnd_ind[i]]->userind;
      lbub[i+j] = (bnd_sense[i] == 'L') ? 'U' : 'L';
      value[i+j] = bnd_val[i];
   }
   p->tm->active_nodes[p->proc_index]->desc.bnd_change = bnd_change;

#endif
   return 0;
}

/*===========================================================================*/

int update_solve_parameters(lp_prob *p)
{
  /* check if feasibility problem */

  LPdata *lp_data = p->lp_data; 
  var_desc **vars = lp_data->vars; 
  int i, n = lp_data->n;
  double ub, lb, obj, etol = 1e-12; 
  //int obj_coeff_cnt = 0;
  double *x = lp_data->x;

  for(i = 0; i < n; i++){
    ub = vars[i]->ub;
    lb = vars[i]->lb; 
    get_objcoef(lp_data, i, &obj);
    
    if(ub > lb + lp_data->lpetol && 
       (obj > etol || obj < -etol)){
      if(x[i] < ub - etol || x[i] > lb + etol){
	break;//obj_coeff_cnt++;
      }       
    }
  }

  //if(obj_coeff_cnt < 1){
  if(i >= n){
    //printf("obj disabled %i\n", p->bc_index);
    p->par.disable_obj = TRUE;
  }
  else 
    p->par.disable_obj = FALSE; 
  
  p->par.no_impr_in_obj = FALSE; 

#ifdef COMPILE_IN_LP  
  bc_node * node = p->tm->active_nodes[p->proc_index];
  int backtrack = 0;
  etol = 100*p->lp_data->lpetol;
  while(node->parent){
    if(node->parent->start_objval > node->start_objval - etol){
      backtrack++;
    }else break;    
    if(backtrack > 4) { 
      p->par.no_impr_in_obj = TRUE; 
      break; 
    }
    node = node->parent;
  }
#endif

  return 0;
}
/*===========================================================================*/
/* this function is called after root node has been processed. we update
 * frequency of cut generation for different cuts depending upon how many cuts
 * were generated and how much time was used
 */
int update_cut_parameters(lp_prob *p)
{
#ifdef USE_CGL_CUTS
   /* TODO: check (a) time (b) if any cuts are actually in the LP */
   lp_stat_desc  lp_stat  = p->lp_stat;
   cgl_params   *par      = &(p->par.cgl);
   cgl_params   *data_par = &(p->lp_data->cgl);

#ifdef COMPILE_IN_LP   

   if(data_par->use_chain_strategy){

      int init_chain_trial_freq = p->par.cgl.chain_trial_freq;
 
#if 0
      double dual_gap = 100.0;
      if(p->has_ub){
	 dual_gap = d_gap(p->ub, p->lp_data->objval, p->mip->obj_offset, p->mip->obj_sense);
      }

      if(dual_gap < 0.25) data_par->chain_status = CGL_CHAIN_STOP;

#endif
      
      
#if 1      
      
      if(data_par->chain_status == CGL_CHAIN_START){
	 data_par->max_chain_trial_num = p->par.cgl.max_chain_trial_num - 
	    p->lp_stat.chain_cuts_trial_num;	 
	 if(data_par->max_chain_trial_num < 0) {
	    data_par->chain_status = CGL_CHAIN_STOP;
	 }
      }

      double b_prog, cut_prog = 0.0;
      char cuts_tried = FALSE;
      double start_objval, end_objval; 
      double act_cut_ratio = (1.0*(p->lp_data->m - p->mip->m))/(p->mip->m);      
      //printf("act-cut %f\n", act_cut_ratio);
      if(data_par->chain_status != CGL_CHAIN_STOP){
	 bc_node * node = p->tm->active_nodes[p->proc_index];
	 
	 data_par->chain_check_index = node->bc_index;
	 b_prog = p->lp_data->objval;
	 node = node->parent;	
	 b_prog -= node->end_objval;	 
	 cuts_tried = node->cuts_tried; 
	 if(cuts_tried){
	    cut_prog = (node->end_objval - node->start_objval);///node->iter_num;
	 }	    
	 start_objval = node->start_objval;
	 end_objval = node->end_objval;
      }
      
      /* TODO: Have these for each cut separately */
      if(data_par->chain_status == CGL_CHAIN_START ||      
	 data_par->chain_status == CGL_CHAIN_CONTINUE ||
	 data_par->chain_status == CGL_CHAIN_CHECK){
	   /* here, we are at the top of the chain, or keep generating
	      due to improvement or we just passed a check_point after
	      paused for a while*/
	 if(cuts_tried){
	    if((b_prog >= 4*cut_prog || fabs(cut_prog/(start_objval + 1e-4)) < data_par->chain_weighted_gap ||
		act_cut_ratio > 0.2)){
	       if(data_par->max_chain_trial_num >= 0){
		  data_par->chain_status = CGL_CHAIN_PAUSE;
		  data_par->chain_trial_freq = init_chain_trial_freq;
	       }else{
		  data_par->chain_status = CGL_CHAIN_STOP;
	       }
	    }else{
	       data_par->chain_status = CGL_CHAIN_CONTINUE;
	       //data_par->max_chain_trial_num = p->par.cgl.max_chain_trial_num;
	    }
	 }else{
	    if(fabs(b_prog/(end_objval + 1e-4)) < 10*par->chain_br_weighted_gap || act_cut_ratio < 0.05){
	       //data_par->max_chain_trial_num--;
	       data_par->chain_status = CGL_CHAIN_CHECK;
	    }else{
	       data_par->chain_status = CGL_CHAIN_PAUSE;
	       data_par->chain_trial_freq = init_chain_trial_freq;
	    }
	 }
      }else if(data_par->chain_status == CGL_CHAIN_PAUSE){
	 if(fabs(b_prog/(end_objval + 1e-4)) < 10*par->chain_br_weighted_gap){
	    data_par->chain_trial_freq--;
	    if(data_par->chain_trial_freq <= 0){
	       data_par->max_chain_trial_num--;
	       data_par->chain_trial_freq = init_chain_trial_freq;
	       data_par->chain_status = CGL_CHAIN_CHECK;
	       data_par->chain_check_index =
		  p->tm->active_nodes[p->proc_index]->bc_index;
	    }
	 }
      }

#if 0
      if(data_par->chain_status == CGL_CHAIN_START){
	 printf("%i CGL-START\n", p->bc_index);	 
      }else if(data_par->chain_status == CGL_CHAIN_CHECK){
	 printf("\t%i CGL-CHECK\n", p->bc_index);	 
      }else if(data_par->chain_status == CGL_CHAIN_STOP){
	 printf("\t%i CGL-STOP\n", p->bc_index);	 
      }else if(data_par->chain_status == CGL_CHAIN_PAUSE){
	 printf("\t%i CGL-PAUSE\n", p->bc_index);
      }else if(data_par->chain_status == CGL_CHAIN_CONTINUE){
	 printf("\t%i CGL-CONT\n", p->bc_index);	 
      }else {
	 printf("\t%i CGL-ELSE\n", p->bc_index);	 
      }
#endif
#endif

      if(data_par->chain_status == CGL_CHAIN_CHECK || 
	 data_par->chain_status == CGL_CHAIN_CONTINUE){
	 p->lp_stat.node_cuts_tried = TRUE;
	 if(data_par->chain_status == CGL_CHAIN_CHECK){
	    p->lp_stat.node_cuts_forced = TRUE; 
	 }
      }
   }
   
#endif

   /* probing cuts */
   if (data_par->generate_cgl_probing_cuts == GENERATE_IF_IN_ROOT && 
       lp_stat.probing_cuts_root<1) {
      data_par->generate_cgl_probing_cuts_freq = -1;
   }
   if (data_par->generate_cgl_probing_cuts == GENERATE_DEFAULT) {

#ifdef COMPILE_IN_LP      
      if(data_par->use_chain_strategy){
	 if(p->bc_level > 0 && p->tm->lp_stat.probing_calls +
	    p->lp_stat.probing_calls > 100 &&
	    p->tm->lp_stat.probing_cuts + p->lp_stat.probing_cuts < 10){
	    data_par->generate_cgl_probing_cuts = DO_NOT_GENERATE;
	 }else{	 
	    if((data_par->chain_status == CGL_CHAIN_CONTINUE ||
		data_par->chain_status == CGL_CHAIN_CHECK)){
	       if(lp_stat.probing_cuts_root >= 1){
		  if(p->mip->mip_inf){		     
		     if(p->mip->mip_inf->cont_var_num > 0){
			if(p->mip->mip_inf->bin_row_ratio > 0.05){
			   if(p->par.cgl.probing_root_max_look < 21 &&
			      p->mip->nz > 1e5 &&
			      p->mip->mip_inf->cont_var_ratio > 0.5){
			      //probably isn't worth it... 
			      if(p->bc_level <= 10){
				 data_par->generate_cgl_probing_cuts_freq = 1;
			      }else{
				 data_par->generate_cgl_probing_cuts_freq = -1;
			      }
			   }else{
			      data_par->generate_cgl_probing_cuts_freq = 1;
			   }
			}else{
			   data_par->generate_cgl_probing_cuts_freq = -1;
			}
		     }else{			
			data_par->generate_cgl_probing_cuts_freq = 1;
		     }
		  }else{
		     data_par->generate_cgl_probing_cuts_freq = 1;
		  }
	       }else{
		  if(p->mip->mip_inf){
		     if(p->mip->m - p->mip->mip_inf->cont_row_num > 0 &&
			p->mip->mip_inf->bin_row_ratio > 0.05){
			if(p->par.cgl.probing_root_max_look < 21 &&
			   p->mip->nz > 1e5 &&
			   p->mip->mip_inf->cont_var_ratio > 0.5){
			   if(p->bc_level <= 10){
			      data_par->generate_cgl_probing_cuts_freq = 1;
			   }else{
			      data_par->generate_cgl_probing_cuts_freq = -1;
			   }
			}else{
			   if(p->bc_level <= 20){			   
			      data_par->generate_cgl_probing_cuts_freq = 1;
			   }else{
			      data_par->generate_cgl_probing_cuts_freq = -1;
			   }
			}
		     }else{
			data_par->generate_cgl_probing_cuts_freq = -1; 
		     }
		  }else{
		     data_par->generate_cgl_probing_cuts_freq = -1;
		  }
	       }
	    }else if(data_par->chain_status == CGL_CHAIN_STOP){
	       data_par->generate_cgl_probing_cuts = DO_NOT_GENERATE;
	    }else{
	       data_par->generate_cgl_probing_cuts_freq = -1;
	    }
	 }
      }else{
#endif	 
	 if (lp_stat.probing_cuts_root<1) {
	    data_par->generate_cgl_probing_cuts_freq = 
	       par->generate_cgl_probing_cuts_freq = 1000;
	 } else if(p->bc_level < 20){
	    data_par->generate_cgl_probing_cuts_freq = 
	       par->generate_cgl_probing_cuts_freq = 50;
	 } else{
	    data_par->generate_cgl_probing_cuts_freq = 
	       par->generate_cgl_probing_cuts_freq = 100;
	 }
#ifdef COMPILE_IN_LP
      }
#endif
   }

   /* twomir cuts */
   if (data_par->generate_cgl_twomir_cuts == GENERATE_IF_IN_ROOT && 
       lp_stat.twomir_cuts_root<1) {
      data_par->generate_cgl_twomir_cuts_freq = -1;
   }
   if (data_par->generate_cgl_twomir_cuts == GENERATE_DEFAULT) {
#ifdef COMPILE_IN_LP
      if(data_par->use_chain_strategy){
	 if(p->bc_level > 0 && p->tm->lp_stat.twomir_calls +
	    p->lp_stat.twomir_calls > 50 &&
	    p->tm->lp_stat.twomir_cuts + p->lp_stat.twomir_cuts < 10){
	    data_par->generate_cgl_twomir_cuts = DO_NOT_GENERATE;
	 }else{	 
	    if((data_par->chain_status == CGL_CHAIN_CONTINUE ||
		data_par->chain_status == CGL_CHAIN_CHECK) &&
	       lp_stat.twomir_cuts_root >= 1){
	       data_par->generate_cgl_twomir_cuts_freq = 1;
	    }else if(data_par->chain_status == CGL_CHAIN_STOP){
	       data_par->generate_cgl_twomir_cuts = DO_NOT_GENERATE;
	    }else{
	       data_par->generate_cgl_twomir_cuts_freq = -1;
	    }
	 }
      }else{
#endif	 
	 if (lp_stat.twomir_cuts_root<1) {
	    data_par->generate_cgl_twomir_cuts_freq = 
	       par->generate_cgl_twomir_cuts_freq = 1000;
	 } else if(p->bc_level < 20){
	    data_par->generate_cgl_twomir_cuts_freq = 
	       par->generate_cgl_twomir_cuts_freq = 50;
	 } else{
	    data_par->generate_cgl_twomir_cuts_freq = 
	       par->generate_cgl_twomir_cuts_freq = 100;
	 }
#ifdef COMPILE_IN_LP
      }
#endif
   }

   /* cliques cuts */
   
   if (data_par->generate_cgl_clique_cuts == GENERATE_IF_IN_ROOT && 
       lp_stat.clique_cuts_root<1) {
      data_par->generate_cgl_clique_cuts_freq = -1;
   }
   if (data_par->generate_cgl_clique_cuts == GENERATE_DEFAULT) {
#ifdef COMPILE_IN_LP
      if(data_par->use_chain_strategy){
	 if(p->bc_level > 0 && p->tm->lp_stat.clique_calls + p->lp_stat.clique_calls > 50 &&
	    p->tm->lp_stat.clique_cuts + p->lp_stat.clique_cuts < 10){
	    data_par->generate_cgl_clique_cuts = DO_NOT_GENERATE;
	 }else{	 
	    if((data_par->chain_status == CGL_CHAIN_CONTINUE ||
		data_par->chain_status == CGL_CHAIN_CHECK) &&
	       lp_stat.clique_cuts_root >= 1) {
	       data_par->generate_cgl_clique_cuts_freq = 1;
	    }else if(data_par->chain_status == CGL_CHAIN_STOP){
	       data_par->generate_cgl_clique_cuts = DO_NOT_GENERATE;
	    }else{
	       data_par->generate_cgl_clique_cuts_freq = -1;
	    }
	 }
      }else{
#endif
	 if (lp_stat.clique_cuts_root<1) {
	    data_par->generate_cgl_clique_cuts_freq = 200;
	 } else {
	    if(p->bc_level < 10){
	       data_par->generate_cgl_clique_cuts_freq = 5;
	    }else {
	       data_par->generate_cgl_clique_cuts_freq = 10;
	    }
	 }
#ifdef COMPILE_IN_LP
      }
#endif
   }
   
   /* flow and cover cuts */
   if (data_par->generate_cgl_flowcover_cuts == GENERATE_IF_IN_ROOT && 
       lp_stat.flowcover_cuts_root<1) {
      data_par->generate_cgl_flowcover_cuts_freq = -1;
   }
   
   if (data_par->generate_cgl_flowcover_cuts == GENERATE_DEFAULT) {
#ifdef COMPILE_IN_LP
      if(data_par->use_chain_strategy){
	 if(p->bc_level > 0 && p->tm->lp_stat.flowcover_calls +
	    p->lp_stat.flowcover_calls > 50 &&
	    p->tm->lp_stat.flowcover_cuts + p->lp_stat.flowcover_cuts < 10){
	    data_par->generate_cgl_flowcover_cuts = DO_NOT_GENERATE;
	 }else{	 	    
	    if((data_par->chain_status == CGL_CHAIN_CONTINUE ||
		data_par->chain_status == CGL_CHAIN_CHECK)){
	       if(lp_stat.flowcover_cuts_root >= 1) { 
		  data_par->generate_cgl_flowcover_cuts_freq = 1;
	       }else{
		  data_par->generate_cgl_flowcover_cuts_freq = -1;
	       }
	    }else if(data_par->chain_status == CGL_CHAIN_STOP){
	       data_par->generate_cgl_flowcover_cuts = DO_NOT_GENERATE;	 
	    }else{
	       data_par->generate_cgl_flowcover_cuts_freq = -1;
	    }
	 }
      }else{
#endif
	 if (lp_stat.flowcover_cuts_root<1) {
	    data_par->generate_cgl_flowcover_cuts_freq = -1;
	 } else {
	    if(p->bc_level < 10){
	       data_par->generate_cgl_flowcover_cuts_freq = 50;
	    }else {
	       data_par->generate_cgl_flowcover_cuts_freq = 100;
	    }
	 }
#ifdef COMPILE_IN_LP
      }
#endif
   }

   /* knapsack */
   
   if (data_par->generate_cgl_knapsack_cuts == GENERATE_IF_IN_ROOT && 
       lp_stat.knapsack_cuts_root<1) {
      data_par->generate_cgl_knapsack_cuts_freq = -1;
   }
   
   if (data_par->generate_cgl_knapsack_cuts == GENERATE_DEFAULT) {
#ifdef COMPILE_IN_LP
      if(data_par->use_chain_strategy){
	 if(p->bc_level > 0 && p->tm->lp_stat.knapsack_calls + p->lp_stat.knapsack_calls > 50 &&
	    p->tm->lp_stat.knapsack_cuts + p->lp_stat.knapsack_cuts < 10){
	    data_par->generate_cgl_knapsack_cuts = DO_NOT_GENERATE;
	 }else{	 	    	    
	    if((data_par->chain_status == CGL_CHAIN_CONTINUE ||
		data_par->chain_status == CGL_CHAIN_CHECK)){
	       if(lp_stat.knapsack_cuts_root >= 1 ) {
		  data_par->generate_cgl_knapsack_cuts_freq = 1;
	       }else{
		  data_par->generate_cgl_knapsack_cuts_freq = -1;
	       }
	    }else if(data_par->chain_status == CGL_CHAIN_STOP){
	       data_par->generate_cgl_knapsack_cuts = DO_NOT_GENERATE;
	    }else{
	       data_par->generate_cgl_knapsack_cuts_freq = -1;
	    }
	 }
      }else{
#endif
	 if (lp_stat.knapsack_cuts_root<1) {
	    data_par->generate_cgl_knapsack_cuts_freq = 200;
	 } else {
	     if(p->bc_level < 10){
		data_par->generate_cgl_knapsack_cuts_freq = 10;
	     }else {
		data_par->generate_cgl_knapsack_cuts_freq = 20;
	     }
	  }
#ifdef COMPILE_IN_LP
       }
#endif
   }

   /* gomory cuts */
   
    if (data_par->generate_cgl_gomory_cuts == GENERATE_IF_IN_ROOT && 
       lp_stat.gomory_cuts_root<1) {
      data_par->generate_cgl_gomory_cuts_freq = -1;
   }
   
   if (data_par->generate_cgl_gomory_cuts == GENERATE_DEFAULT) {
#ifdef COMPILE_IN_LP
      if(data_par->use_chain_strategy){

	 //printf("gomory_nz: %.2f\n", p->gomory_nz);
	 if (p->lp_stat.gomory_nz > 5e6){
	    data_par->generate_cgl_gomory_cuts = DO_NOT_GENERATE;
	 }
	 if(p->bc_level > 0 && p->tm->lp_stat.gomory_calls + p->lp_stat.gomory_calls > 200 &&
	    p->tm->lp_stat.gomory_cuts + p->lp_stat.gomory_cuts < 10){
	    data_par->generate_cgl_gomory_cuts = DO_NOT_GENERATE;
	 }else{	 	    	    
	    if((data_par->chain_status == CGL_CHAIN_CONTINUE ||
		data_par->chain_status == CGL_CHAIN_CHECK)){
	       data_par->generate_cgl_gomory_cuts_freq = 1;
	    }else if(data_par->chain_status == CGL_CHAIN_STOP){
	       data_par->generate_cgl_gomory_cuts = DO_NOT_GENERATE;
	    }else{
	       data_par->generate_cgl_gomory_cuts_freq = -1;
	    }
	 }
      }else{
#endif
	 if (lp_stat.gomory_cuts_root<1) {
	    data_par->generate_cgl_gomory_cuts_freq = 100;
	 } else {
	    if(p->bc_level < 10){
	       data_par->generate_cgl_gomory_cuts_freq = 5;
	    }else {
	       data_par->generate_cgl_gomory_cuts_freq = 10;
	    }
	 }
#ifdef COMPILE_IN_LP
      }
#endif
   }   

#endif
   return 0;
}

/*===========================================================================*/
int generate_cgl_cuts_new(lp_prob *p, int *num_cuts, cut_data ***cuts, 
      int send_to_pool, int *bound_changes)
{

#ifdef USE_CGL_CUTS
   int i, should_stop = FALSE, repeat_with_long = TRUE, max_cut_length;
   OsiCuts cutlist;
   const int n                 = p->lp_data->n;
   OsiXSolverInterface  *si    = p->lp_data->si;
   var_desc             **vars = p->lp_data->vars;
   int                  was_tried = FALSE;
   
   if (p->iter_num < 2) {
     for (i = 0; i < n; i++) {
	if (vars[i]->is_int) { // integer or binary
            si->setInteger(i);
         }
      }  
   }

#ifdef COMPILE_IN_LP
   if(p->bc_level < 1 && p->iter_num < 2){
      int row_den = (int)(1.0*p->mip->nz/p->mip->m) + 1;
      /* all previous */
      if(p->mip->mip_inf){
	 //printf("max_col_size: %i\t", p->mip->mip_inf->max_col_size);
	 //printf("row den: %i\t, max_row_size: %i\t", row_den,
	 //p->mip->mip_inf->max_row_size);
	 	 
	 //printf("sos_ratio %f \t", bin_sos_ratio);
	 //printf("cont_bin_ratio %f\n", cont_ratio);

	 if(p->mip->mip_inf->sos_bin_row_ratio > 0.6 &&
	    p->mip->mip_inf->sos_bin_row_ratio < 0.9){
	    p->par.max_cut_length *= 2;
	 }
	 
	 if(p->mip->mip_inf->max_row_ratio < 0.01 &&
	    p->mip->mip_inf->prob_type != BIN_CONT_TYPE){
	    p->par.cgl.chain_trial_freq = (int)1.5*p->par.cgl.chain_trial_freq;
	 }
	 if(p->mip->mip_inf->cont_var_ratio > 0.1 &&
	    p->mip->mip_inf->max_row_ratio > 0.1)
	    p->par.max_cut_length = p->par.max_cut_length/3 + 1;
	
	 if(p->mip->mip_inf->max_row_size <= 500){
	    int max_const_size = p->mip->mip_inf->max_row_size;
	    if(p->mip->mip_inf->prob_type == BINARY_TYPE ||
	       p->mip->mip_inf->prob_type == BIN_CONT_TYPE){
	       if(p->mip->mip_inf->max_row_ratio < 0.05){
		  max_const_size = 4*max_const_size;
	       }else {
		  max_const_size = 5*max_const_size;
	       }
	    }else{
	       if(p->mip->mip_inf->max_row_ratio < 0.01){
		  max_const_size += row_den;
	       }else {
		  max_const_size = (int)(max_const_size * 3.5);
	       }
	    }

	    p->par.max_cut_length =
	       MIN(MAX(p->mip->mip_inf->max_row_size,
		       MIN(((int)(1.0133 * p->mip->mip_inf->mat_density *
				  (p->mip->m + 1)* p->mip->n) -
			    p->mip->nz + row_den) + 6,
			   max_const_size)),
		   p->par.max_cut_length);
	 }else{
	    if(1.0*p->mip->mip_inf->max_row_size/p->mip->n > 0.5){
	       p->par.max_cut_length =
		  MIN(p->mip->mip_inf->max_row_size,
		      (int)(1.0*p->par.max_cut_length *
			    p->mip->mip_inf->max_row_size/500.0) + row_den);
			    
	    }else{
	       p->par.max_cut_length = MAX(2*p->mip->mip_inf->max_row_size,
					   (int)(1.0*p->par.max_cut_length *
						 p->mip->mip_inf->max_row_size/
						 500.0) + row_den);	       
	    }
	 }
      }else{
	 p->par.max_cut_length =
	    MIN(p->par.max_cut_length,
		(int)(5.0*row_den*p->mip->n/(row_den + p->mip->n)) + 5);
		      
      }
      //     printf("sos/m %f\n", (1.0*p->mip->mip_inf->binary_sos_row_num)/p->mip->m);
      //  printf("max_cut_length %i\n", p->par.max_cut_length);
   }
#endif
   if(p->bc_level < 1 && p->iter_num < 2){   

     for (i=0; i<CGL_NUM_GENERATORS; i++) {
       p->par.best_violation[i] = 0.0;
       p->par.best_violation_length[i] = p->par.max_cut_length;
     }
     //p->par.best_violation_length = p->par.max_cut_length;
#ifdef COMPILE_IN_LP
     if(p->par.verbosity > 1){
       printf("c-length - max_row - max-col - dens: %i - %i - %i - %f\n", p->par.max_cut_length, 
	      p->mip->mip_inf->max_row_size, p->mip->mip_inf->max_col_size, 
	      p->mip->mip_inf->mat_density);
     }
#endif
   }

   max_cut_length = p->par.max_cut_length; 
   p->par.tried_long_cuts = TRUE;
   if (p->par.tried_long_cuts == TRUE) {
      repeat_with_long = FALSE;
   }
   
   i = 0; 

   for (; i<CGL_NUM_GENERATORS; i++) {
      //printf("c_l: %i %i \n", i, p->par.max_cut_length);
      if(i > -1) generate_cgl_cut_of_type(p, i, &cutlist, &was_tried);	 
      //if(cutlist.sizeRowCuts() > 0){
      check_and_add_cgl_cuts(p, i, cuts, num_cuts, bound_changes, &cutlist, 
			     send_to_pool);
      
      should_stop_adding_cgl_cuts(p, i, &should_stop);
      if(i < 0 && *num_cuts > 0) should_stop = TRUE;
      //}
      if (should_stop == TRUE) {
         break;
      }
      if (i==CGL_NUM_GENERATORS-1 && p->bc_index < 1 && *num_cuts < 1 && 
            repeat_with_long == TRUE) {
         p->par.max_cut_length = 1000;
         i = -1;
         repeat_with_long = FALSE;
         p->par.tried_long_cuts = TRUE;
      }
   }

   p->par.max_cut_length = max_cut_length;

   add_col_cuts(p, &cutlist, bound_changes);
   if (was_tried == TRUE && p->bc_index > 0) {
      p->lp_stat.num_cut_iters_in_path++;
   }

#endif
   return 0;
}

/*===========================================================================*/
int should_use_cgl_generator(lp_prob *p, int *should_generate, 
      int which_generator, void *generator)
{

#ifdef USE_CGL_CUTS
   int bc_index = p->bc_index;
   int bc_level = p->bc_level;
   int max_cut_length = p->par.max_cut_length;
   cgl_params   *data_par = &(p->lp_data->cgl);   

   *should_generate = FALSE;

   switch (which_generator) {
    case CGL_PROBING_GENERATOR:
      {
	 CglProbing *probing = (CglProbing *)generator;
         int param = p->lp_data->cgl.generate_cgl_probing_cuts;
         int freq  = p->lp_data->cgl.generate_cgl_probing_cuts_freq;
	 int max_bc_level = p->par.cgl.probing_max_depth;
         if (param < 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_DEFAULT &&
		    (bc_level > max_bc_level || 
		     freq < 1 || bc_index % freq != 0 ||
		     data_par->chain_status == CGL_CHAIN_PAUSE)){
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_ONLY_IN_ROOT && bc_index > 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_IF_IN_ROOT && (freq < 1 || 
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_PERIODICALLY && (freq < 1 || 
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } 


#ifdef COMPILE_IN_LP
	 if(data_par->use_chain_strategy){
	    probing->setRowCuts(3); 
	    probing->setMode(2);
	    probing->setUsingObjective(1);
	    
	    probing->setMaxPassRoot(1);
	    if(p->bc_level < 1){
	       if(p->iter_num < 2){
		  probing->setMaxElementsRoot(10000);
		  if(p->mip->nz > 2e5){
		     probing->setMaxProbeRoot(25);
		  }else if(p->mip->nz > 1e5){
		     probing->setMaxProbeRoot(50);		  
		  }else if(p->mip->nz > 0.75e5){
		     probing->setMaxProbeRoot(75);
		  }else if(p->mip->nz > 0.5e5){
		     probing->setMaxProbeRoot(100);
		  }else{
		     probing->setMaxProbeRoot(200);
		  }

		  if(p->mip->mip_inf){
		     p->par.cgl.probing_root_max_look =
			(int)((1e5/p->mip->nz) *
			      (5e4/p->mip->mip_inf->max_row_size)) + 1;
		     if(p->mip->mip_inf->binary_sos_row_num > 0) {
			if(p->mip->mip_inf->sos_bin_row_ratio > 0.05){
			   p->par.cgl.probing_root_max_look =
			      (int)(p->par.cgl.probing_root_max_look/
				    (200.0*p->mip->mip_inf->sos_bin_row_ratio)) + 1;
			}
		     }

		     p->par.cgl.probing_root_max_look =
			MIN(200,MAX(p->par.cgl.probing_root_max_look, 20));

		  }else{
		     p->par.cgl.probing_root_max_look =
			MIN(200,MAX((int)(1e5/p->mip->nz * 5e4/p->mip->n) + 1,
				    10));
		  }
	       }else{
		  if(p->par.cgl.probing_is_expensive){
		     p->par.cgl.probing_root_max_look =
			MIN(50,MAX((int)p->par.cgl.probing_root_max_look/2 + 10,
				   5));
		  }
	       }
	       probing->setMaxLookRoot(p->par.cgl.probing_root_max_look);
	       //printf("max_look: %i\n", p->par.cgl.probing_root_max_look);
	       // printf("bin_row_num %i\n", p->mip->mip_inf->binary_row_num);
	    }else{
	       if(p->mip->nz > 1e5){
		  probing->setMaxProbeRoot(50);
	       }else if(p->mip->nz > 0.75e5){
		  probing->setMaxProbeRoot(75);
	       }else{
		  probing->setMaxProbeRoot(100);
	       }
	       
	       probing->setMaxElementsRoot(1000);
	       probing->setMaxLookRoot 
		  (MAX(11, (int)(p->par.cgl.probing_root_max_look)/2 + 10));

	       if(p->par.cgl.probing_is_expensive){
		  probing->setMaxLookRoot
		     (MAX(5,(int)(p->par.cgl.probing_root_max_look)/5 + 1));
	       }
	    }
	 }else{
#endif
	    if(p->bc_index < 1){
	       if((p->lp_stat.lp_max_iter_num < 1000 &&
		   p->comp_times.probing_cuts > 10*p->comp_times.lp) ||
		  (p->lp_stat.lp_max_iter_num >= 1000 &&
		   p->comp_times.probing_cuts > 2*p->comp_times.lp)){
		  p->par.cgl.probing_is_expensive = TRUE;
	       }else{
		  p->par.cgl.probing_is_expensive = FALSE;
	       }
	    }else{
	       if (p->comp_times.probing_cuts > 2*p->comp_times.lp){
		  p->par.cgl.probing_is_expensive = TRUE;
	       }else{
		  p->par.cgl.probing_is_expensive = FALSE;
	       }
	    }

	    probing->setRowCuts(3); 
	    probing->setMode(2);
	    probing->setUsingObjective(1);
	    
	    if (p->bc_index < 1 &&
		!p->lp_data->cgl.probing_is_expensive) {
	       probing->setMaxPass(10); /* default is 3 */
	       probing->setMaxPassRoot(10); /* default is 3 */
	       probing->setMaxElements(10000);  /* default is 1000 */
	       probing->setMaxElementsRoot(10000); /* default is 10000 */
	       probing->setMaxLook(100);    /* default is 50 */
	       probing->setMaxLookRoot(100);    /* default is 50 */
	       probing->setMaxProbe(200);   /* default is 100 */
	       probing->setMaxProbeRoot(200);   /* default is 100 */
	       if(p->bc_level > 0){
		  probing->setMaxElementsRoot(1000);  /* default is 1000 */
		  probing->setMaxLookRoot(50);    /* default is 50 */
	       }
	    }
#ifdef COMPILE_IN_LP
	 }
#endif
         *should_generate = TRUE;
         p->lp_stat.probing_calls++;
         break;
      }
    case CGL_CLIQUE_GENERATOR:
      {
         CglClique *clique = (CglClique *)generator;
         int param = p->lp_data->cgl.generate_cgl_clique_cuts;
         int freq  = p->lp_data->cgl.generate_cgl_clique_cuts_freq;
	 int max_bc_level = p->par.cgl.clique_max_depth;
         if (param < 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_DEFAULT &&
		    (bc_level > max_bc_level ||
		     freq < 0 || bc_index % freq != 0 ||
		     data_par->chain_status == CGL_CHAIN_PAUSE)){
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_ONLY_IN_ROOT && bc_index > 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_IF_IN_ROOT && (freq < 0 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_PERIODICALLY && (freq < 0 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } 
         *should_generate = TRUE;
         clique->setStarCliqueReport(FALSE);
         clique->setRowCliqueReport(FALSE);
	 //clique->setDoStarClique(FALSE);
	 //clique->setStarCliqueCandidateLengthThreshold(6);
	 //clique->setRowCliqueCandidateLengthThreshold(6);
         p->lp_stat.clique_calls++;
         break;
      }
    case CGL_KNAPSACK_GENERATOR:
      {
         CglKnapsackCover *knapsack = (CglKnapsackCover *)generator;
         int param = p->lp_data->cgl.generate_cgl_knapsack_cuts;
         int freq  = p->lp_data->cgl.generate_cgl_knapsack_cuts_freq;
	 int max_bc_level = p->par.cgl.knapsack_max_depth;
         if (param < 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_DEFAULT &&
		    (bc_level > max_bc_level ||
		     freq < 1 || bc_index % freq != 0  ||
		     data_par->chain_status == CGL_CHAIN_PAUSE)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_ONLY_IN_ROOT && bc_index > 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_IF_IN_ROOT && (freq < 1 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_PERIODICALLY && (freq < 1 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } 
         *should_generate = TRUE;
         knapsack->setMaxInKnapsack(max_cut_length); // default is 50
         knapsack->switchOffExpensive(); // gets into infinite loop if on 
         p->lp_stat.knapsack_calls++;
         break;
      }
    case CGL_GOMORY_GENERATOR:
      {
         CglGomory *gomory = (CglGomory *)generator;
         int param = p->lp_data->cgl.generate_cgl_gomory_cuts;
         int freq  = p->lp_data->cgl.generate_cgl_gomory_cuts_freq;
	 int max_bc_level = p->par.cgl.gomory_max_depth;
         if (param < 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_DEFAULT &&
		    (bc_level > max_bc_level ||
		     freq < 1 || bc_index % freq != 0  ||
		     data_par->chain_status == CGL_CHAIN_PAUSE)){
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_ONLY_IN_ROOT && bc_index > 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_IF_IN_ROOT && (freq < 1 || 
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_PERIODICALLY && (freq < 1 || 
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         }
	 gomory->setLimit(max_cut_length);
	 //if(p->bc_index < 1) {
	 //  gomory->setAway(100*p->lp_data->lpetol);
	 //}
	 //gomory->setAwayAtRoot(100*p->lp_data->lpetol);
	 *should_generate = TRUE;
         p->lp_stat.gomory_calls++;
         break;
      }
    case CGL_TWOMIR_GENERATOR:
      {
         CglTwomir *twomir = (CglTwomir *)generator;
         int param = p->lp_data->cgl.generate_cgl_twomir_cuts;
         int freq  = p->lp_data->cgl.generate_cgl_twomir_cuts_freq;
	 int max_bc_level = p->par.cgl.twomir_max_depth;
         if (param < 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_DEFAULT &&
		    (bc_level > max_bc_level ||
		     freq < 1 || bc_index % freq != 0  ||
		     data_par->chain_status == CGL_CHAIN_PAUSE)){
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_ONLY_IN_ROOT && bc_index > 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_IF_IN_ROOT && (freq < 1 ||
                  bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_PERIODICALLY && (freq < 1 ||
                  bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } 
         *should_generate = TRUE;
         twomir->setMaxElements(max_cut_length);
         twomir->setCutTypes (TRUE, TRUE, TRUE, TRUE);
         p->lp_stat.twomir_calls++;
         break;
      }
    case CGL_FLOWCOVER_GENERATOR:
      {
         CglFlowCover *flowcover = (CglFlowCover *)generator;
         int param = p->lp_data->cgl.generate_cgl_flowcover_cuts;
         int freq  = p->lp_data->cgl.generate_cgl_flowcover_cuts_freq;
	 int max_bc_level = p->par.cgl.flowcover_max_depth;
         if (param < 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_DEFAULT &&
		    (bc_level > max_bc_level ||
		     freq < 1 || bc_index % freq != 0  ||
		     data_par->chain_status == CGL_CHAIN_PAUSE)) { 
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_ONLY_IN_ROOT && bc_index > 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_IF_IN_ROOT && (freq < 1 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_PERIODICALLY && (freq < 1 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } 
         *should_generate = TRUE;
         flowcover->setNumFlowCuts(0); //needs to be called because static
         p->lp_stat.flowcover_calls++;
         break;
      }
   case CGL_ODDHOLE_GENERATOR:
      {
	 CglOddHole *oddhole = (CglOddHole *)generator;
	 int param = p->lp_data->cgl.generate_cgl_oddhole_cuts;
	 int freq  = p->lp_data->cgl.generate_cgl_oddhole_cuts_freq;
	 int max_bc_level = p->par.cgl.oddhole_max_depth;
	 if (param < 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_DEFAULT &&
		    (bc_level > max_bc_level ||
		     freq < 1 || bc_index % freq != 0  ||
		     data_par->chain_status == CGL_CHAIN_PAUSE)){
	    *should_generate = FALSE;
	    break;
         } else if (param == GENERATE_ONLY_IN_ROOT && bc_index > 0) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_IF_IN_ROOT && (freq < 1 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } else if (param == GENERATE_PERIODICALLY && (freq < 1 ||
               bc_index % freq != 0)) {
            *should_generate = FALSE;
            break;
         } 
         *should_generate = TRUE;
	 oddhole->setMinimumViolation(0.005);
	 oddhole->setMinimumViolationPer(0.00002);
	 oddhole->setMaximumEntries(max_cut_length);
         p->lp_stat.oddhole_calls++;
         break;
      }
   }
#endif
   return 0;
}

/*===========================================================================*/
#ifdef USE_CGL_CUTS
int generate_cgl_cut_of_type(lp_prob *p, int i, OsiCuts *cutlist_p, 
      int *was_tried)
{
   OsiCuts cutlist = *cutlist_p;
   int should_generate = FALSE;
   double total_time, cut_time;   
   
   /* two times is necessary */
   cut_time     = used_time(&total_time);
   cut_time     = used_time(&total_time);
   
   switch (i) {
     case CGL_PROBING_GENERATOR:
       {
	  double mark_time = 0;
	  CglProbing *probing = new CglProbing;
	  should_use_cgl_generator(p, &should_generate, i, (void *)probing);
         if (should_generate == TRUE) {
            probing->generateCuts(*(p->lp_data->si), cutlist);
            *was_tried = TRUE;
         }
         delete probing;
         cut_time     = used_time(&total_time);
         p->comp_times.probing_cuts += cut_time - mark_time;
         break;
      }
    case CGL_CLIQUE_GENERATOR:
      {
         CglClique *clique = new CglClique;
         should_use_cgl_generator(p, &should_generate, i, (void *)clique);
         if (should_generate == TRUE) {
            clique->generateCuts(*(p->lp_data->si), cutlist);
            *was_tried = TRUE;
         }
         delete clique;
         cut_time     = used_time(&total_time);
         p->comp_times.clique_cuts += cut_time;
         break;
      }
    case CGL_KNAPSACK_GENERATOR:
      {
         CglKnapsackCover *knapsack = new CglKnapsackCover;
         should_use_cgl_generator(p, &should_generate, i, (void *)knapsack);
         if (should_generate == TRUE) {
            knapsack->generateCuts(*(p->lp_data->si), cutlist);
            *was_tried = TRUE;
         }
         delete knapsack;
         cut_time     = used_time(&total_time);
         p->comp_times.knapsack_cuts += cut_time;
         break;
      }
    case CGL_GOMORY_GENERATOR:
      {
         CglGomory *gomory = new CglGomory;
         should_use_cgl_generator(p, &should_generate, i, (void *)gomory);
         if (should_generate == TRUE) {
	    gomory->generateCuts(*(p->lp_data->si), cutlist);
	    *was_tried = TRUE;	    
         }
         delete gomory;
         cut_time     = used_time(&total_time);
         p->comp_times.gomory_cuts += cut_time;
         break;
      }
    case CGL_TWOMIR_GENERATOR:
      {
         CglTwomir *twomir = new CglTwomir;
         should_use_cgl_generator(p, &should_generate, i, (void *)twomir);
         if (should_generate == TRUE) {
            twomir->generateCuts(*(p->lp_data->si), cutlist);
            *was_tried = TRUE;
         }
         delete twomir;
         cut_time     = used_time(&total_time);
         p->comp_times.twomir_cuts += cut_time;
         break;
      }
    case CGL_FLOWCOVER_GENERATOR:
      {
         CglFlowCover *flowcover = new CglFlowCover;
         should_use_cgl_generator(p, &should_generate, i, (void *)flowcover);
         if (should_generate == TRUE) {
            flowcover->generateCuts(*(p->lp_data->si), cutlist);
            *was_tried = TRUE;
         }
         delete flowcover;
         cut_time     = used_time(&total_time);
         p->comp_times.flowcover_cuts += cut_time;
         break;
      }
    case CGL_ODDHOLE_GENERATOR:
      {
	CglOddHole *oddhole = new CglOddHole;
	should_use_cgl_generator(p, &should_generate, i, (void *)oddhole);
	if (should_generate == TRUE) {
	  oddhole->generateCuts(*(p->lp_data->si), cutlist);
	  *was_tried = TRUE;
	}
	delete oddhole;
	cut_time     = used_time(&total_time);
	p->comp_times.oddhole_cuts += cut_time;
	break;
      }
   }
   *cutlist_p = cutlist;
   p->comp_times.cuts += cut_time;
   return 0;
}
#endif

/*===========================================================================*/
#ifdef USE_CGL_CUTS
int check_and_add_cgl_cuts(lp_prob *p, int generator, cut_data ***cuts, 
			   int *num_cuts, int *bound_changes, OsiCuts *cutlist, int send_to_pool) 
{
   int i, k, num_row_cuts, *accepted_ind = NULL, num_elements,
      *indices, discard_cut, num_poor_quality = 0, num_unviolated = 0,
      num_duplicate = 0, *matind; 
   int    max_elements = p->par.max_cut_length, 
      verbosity = p->par.verbosity;
   LPdata       *lp_data = p->lp_data;
   int          *tmp_matind = lp_data->tmp.i1;
   double       *hashes = NULL, *elements, rhs, max_coeff, min_coeff, hash_value, 
                violation, *matval, total_time, cut_time;
   double       *random_hash = lp_data->random_hash;
   const double lpetol = lp_data->lpetol;
   const double etol10 = lpetol * 10;
   //const double etol50 = lpetol * 50;
   //const double etol500 = lpetol * 500;
   const double etol100 = lpetol * 100;
   const double etol1000 = lpetol * 1000;
   const double *x     = lp_data->x;
   OsiRowCut    row_cut;
   var_desc     **vars = lp_data->vars;
   const int    is_userind_in_order = p->par.is_userind_in_order;
   cut_data     *sym_cut;
   int update_cut_length = FALSE;
   
   /* two times is necessary */
   cut_time     = used_time(&total_time);
   cut_time     = used_time(&total_time);

   num_row_cuts = cutlist->sizeRowCuts();

   //if(num_row_cuts > 0){
   // hashes       = (double *) malloc(num_row_cuts*DSIZE);
   //is_deleted   = (int *) calloc(num_row_cuts, ISIZE);
   // accepted_ind =   (int *) malloc(num_row_cuts* ISIZE);
   // cut_size     = (int *) calloc(num_row_cuts, ISIZE);
   //}
   
   if(lp_data->hashes_num < num_row_cuts + *num_cuts){
      lp_data->hashes_num = 5000 + (num_row_cuts + *num_cuts); 
      lp_data->hashes = (double *)malloc(DSIZE*lp_data->hashes_num);
   }

   if(lp_data->accepted_num < num_row_cuts){
      lp_data->accepted_num = 5000 + num_row_cuts;
      lp_data->accepted_ind = (int *)malloc(ISIZE*lp_data->accepted_num);
   }

   hashes = lp_data->hashes;
   accepted_ind = lp_data->accepted_ind;   
   
   int accepted_cnt = 0; 
   //j = 0;
   double fabs_value = 0.0; 

   //int v_level; 
   double coeff_ratio; 
   for (i=0; i<num_row_cuts; i++) {
      /* check for violation, duplicacy, quality of coefficients, length */
      row_cut = cutlist->rowCut(i);
      num_elements = row_cut.row().getNumElements();
      //cut_size[accepted_cnt] = num_elements;
      indices = const_cast<int *> (row_cut.row().getIndices());
      elements = const_cast<double *> (row_cut.row().getElements());
      rhs = row_cut.rhs();
      discard_cut = FALSE;
      max_coeff = 0;
      min_coeff = DBL_MAX;
      
      if (verbosity>10) {
         row_cut.print();
      }

      if (num_elements > max_elements){
         PRINT(verbosity,5,("Threw out cut because its length %d is too "
                  "high.\n\n\n", num_elements));
	 //printf("%i %i %i \n", num_elements, max_elements, generator); 
         num_poor_quality++;
         //is_deleted[i] = TRUE;
         continue;
      }
      
      /* hash value, min, max, violation */
      hash_value = 0;
      violation = 0;
      int is_int = TRUE; 
      for (int el_num=0; el_num<num_elements; el_num++) {
	 
	 if(!(lp_data->vars[indices[el_num]]->is_int)) is_int = FALSE; 

	 // printf("%f\n", elements[el_num]);
	 fabs_value = fabs(elements[el_num]); 
         if (fabs_value>max_coeff) {
            max_coeff = fabs_value; 
         }
         if (fabs_value < min_coeff) {
            min_coeff = fabs_value;
         }
         tmp_matind[el_num] = vars[indices[el_num]]->userind;
         hash_value += elements[el_num]*random_hash[tmp_matind[el_num]];
         violation += elements[el_num]*x[tmp_matind[el_num]];
      }
      //hashes[*num_cuts + accepted_cnt] = hash_value;
      /* see rhs as well */
#if 1
      fabs_value = fabs(rhs); 
      if (fabs_value > lpetol) {
         if (fabs_value < min_coeff) { 
            min_coeff = fabs_value;
         }
         if (fabs_value > max_coeff) {
            max_coeff = fabs_value; 
         }
      }
#endif
      switch (row_cut.sense()) {
       case 'L':
         violation -= rhs;
         break;
       case 'G':
         violation = rhs - violation;
         break;
       case 'E':
         violation = fabs(rhs - violation);
         break;
      }
      //v_level = 1; 
      coeff_ratio = min_coeff/max_coeff; 
      /* check quality */
      if (num_elements>0) {
         if ( (max_coeff > 0 && coeff_ratio < etol1000)||
	      (min_coeff > 0 && min_coeff < etol1000) ) {
            PRINT(verbosity,5,("Threw out cut because of bad coeffs.\n"));
	    //printf("%f %f %f\n\n", min_coeff, max_coeff, etol1000);
	    num_poor_quality++;
	    //is_deleted[i] = TRUE;
	    continue;
         }
      }
      
      if (violation < etol10){//*v_level){
         PRINT(verbosity,5,("violation = %f. Threw out cut.\n", 
			    violation));
         num_unviolated++;
         //is_deleted[i] = TRUE;
         continue;
      }//else printf("violation - %f \n", violation);

      /* check if sense is 'R' */
      if (row_cut.sense()=='R') {
         PRINT(verbosity,5,("cut #%d has a range. thrown out.\n", i));
         //is_deleted[i] = TRUE;
         continue;
      }

      if(p->par.best_violation[generator] < lpetol){
	 update_cut_length = TRUE;
      }
	 
      if(update_cut_length){
	if(violation > p->par.best_violation[generator]){
	  //printf("%i - %f\n", generator, violation);
	  p->par.best_violation[generator] = violation;
	  p->par.best_violation_length[generator] = 4*num_elements;
	}
      }

      /* cut is accepted. congratulations. */
      hashes[*num_cuts + accepted_cnt] = hash_value; 
      accepted_ind[accepted_cnt] = i;
      accepted_cnt++; 

      if (generator == CGL_GOMORY_GENERATOR){
	 p->lp_stat.gomory_nz += num_elements; 
      }

      //j++;
#ifdef COMPILE_IN_LP
      if(p->bc_index < 1 && p->mip->mip_inf && ( generator == CGL_PROBING_GENERATOR || 
						 generator == CGL_CLIQUE_GENERATOR ||
						 generator == CGL_KNAPSACK_GENERATOR)){	 
	 add_cut_to_mip_inf(p, num_elements, indices, elements, rhs, row_cut.sense());	 
      }      
#endif
   }

   /* check for duplicates */
   hashes += *num_cuts; 
   qsort_di(hashes, accepted_ind, accepted_cnt);
   int l_ind, r_ind, c_ind;
   int move_ratio = num_row_cuts + 100; 
   for(l_ind = 0; l_ind < accepted_cnt;){
      c_ind = accepted_ind[l_ind]; 
      accepted_ind[l_ind] += move_ratio; 
      for(r_ind = l_ind + 1; r_ind < accepted_cnt; r_ind++){
	 if(fabs(hashes[l_ind] - hashes[r_ind]) < lpetol){
            PRINT(verbosity,5,("cut #%i is same as cut #%i\n", c_ind, accepted_ind[r_ind]));
            num_duplicate++;
            //is_deleted[i] = TRUE;
	    r_ind++;
	 }else{
	    l_ind = r_ind; 
	    break;
	 }
      }
      if(r_ind >= accepted_cnt) break; 
   }

   r_ind = accepted_cnt;
   accepted_cnt = 0; 
   for(l_ind = 0; l_ind < r_ind; l_ind++){
      c_ind = accepted_ind[l_ind] - move_ratio;
      if(c_ind >= 0){
	 hashes[accepted_cnt] = hashes[l_ind];
	 accepted_ind[accepted_cnt++] = c_ind;
      }
   }
   hashes -= *num_cuts; 

   int * rc_ind = 0; 
   int rc_cnt = 0; 
   if (p->bc_index > 0 && p->mip->mip_inf && p->mip->mip_inf->c_num && generator == CGL_NUM_GENERATORS - 1){
      MIPinfo * mip_inf = p->mip->mip_inf; 
      rc_ind = mip_inf->c_tmp;
      int c_num = mip_inf->c_num;
      int is_identical; 
      /* check only for hash value and violation */
      for(int t_num = 0; t_num < c_num; t_num++){
	 num_elements = mip_inf->c_beg[t_num + 1] - mip_inf->c_beg[t_num];
	 elements = mip_inf->c_val + mip_inf->c_beg[t_num]; 
	 indices = mip_inf->c_ind + mip_inf->c_beg[t_num]; 
	 rhs = mip_inf->c_rhs[t_num];
	 hash_value = 0.0; 
	 violation = 0.0;
	 is_identical = FALSE;
	 
	 for (int el_num=0; el_num<num_elements; el_num++) {
	    tmp_matind[el_num] = vars[indices[el_num]]->userind;
	    if(*num_cuts + accepted_cnt > 0) hash_value += elements[el_num]*random_hash[tmp_matind[el_num]];
	    violation += elements[el_num]*x[tmp_matind[el_num]];
	 }

	 switch (mip_inf->c_sense[t_num]) {
	  case 'L':
	    violation -= rhs;
	    break;
	  case 'G':
	    violation = rhs - violation;
	    break;
	  case 'E':
	    violation = fabs(rhs - violation);
	    break;
	 }

	 if (violation < etol100){
	    continue;
	 }

	 for(k = 0; k < accepted_cnt + *num_cuts; k++){
	    if (fabs(hashes[k]-hash_value) < lpetol) {		
	       is_identical = TRUE; 
	       break;
	    }
	 }

	 if (is_identical){
	    continue;
	 }	 

	 rc_ind[rc_cnt] = t_num;
	 rc_cnt++;
      }
   }   

   //if(rc_cnt > 0) printf("root cuts added %i %i\n", p->bc_index, rc_cnt);
   
   int new_cut_num = accepted_cnt + rc_cnt;   
   
   /* copy the accepted cuts */
   if(new_cut_num > 0){
      if (*cuts){
	 *cuts = (cut_data **)realloc(*cuts, (*num_cuts+new_cut_num)*sizeof(cut_data *));
      }else{
	 *cuts = (cut_data **)malloc(new_cut_num*sizeof(cut_data *));
      }
   }
   
   k = *num_cuts;
   
   int p_cnt = 0;
   int ind = 0; 
   char sense; double range;
   
   //for (i=0; i<num_row_cuts + rc_cnt; i++) {
   for (i=0; i<new_cut_num; i++) {
      if (i < accepted_cnt){
	 //if(is_deleted[i] == TRUE) {
	 //  continue;
	 //}
	 ind = accepted_ind[i]; 
	 //if(ind - move_ratio < 0) continue; 
	 row_cut = cutlist->rowCut(ind);
	 num_elements = row_cut.row().getNumElements();
	 //PRINT(verbosity, -1,("length = %d \n", num_elements));
	 indices = const_cast<int *> (row_cut.row().getIndices());
	 elements = const_cast<double *> (row_cut.row().getElements());
	 rhs = row_cut.rhs();
	 sense = row_cut.sense();
	 range = row_cut.range();
      }else{
	 ind = rc_ind[i - accepted_cnt];
	 num_elements = p->mip->mip_inf->c_beg[ind + 1] -
	    p->mip->mip_inf->c_beg[ind]; 
	 indices = p->mip->mip_inf->c_ind + p->mip->mip_inf->c_beg[ind];
	 elements = p->mip->mip_inf->c_val + p->mip->mip_inf->c_beg[ind];
	 rhs = p->mip->mip_inf->c_rhs[ind];
	 sense = p->mip->mip_inf->c_sense[ind];
	 range = 0;//sense = p->mip->mip_inf->c_sense[c_ind];
      }
      (*cuts)[k] =  (cut_data *) calloc(1, sizeof(cut_data));
      sym_cut    = (*cuts)[k];
      sym_cut->type = EXPLICIT_ROW;
      sym_cut->rhs = rhs;
      sym_cut->range = range;
      //sym_cut->size = (num_elements * (int)((ISIZE + DSIZE) + DSIZE));
      sym_cut->size = (int)(DSIZE + num_elements * (ISIZE + DSIZE));
      sym_cut->coef = (char *) malloc (sym_cut->size);
      sym_cut->sense = sense;
      ((double *) (sym_cut->coef))[0] = 0; // otherwise valgrind complains.
      ((int *) (sym_cut->coef))[0] = num_elements;

      //Here, we have to pad the initial int to avoid misalignment, so we
      //add DSIZE bytes to get to a double boundary
      matval = (double *) (sym_cut->coef + DSIZE);
      matind = (int *) (sym_cut->coef + (num_elements + 1)*DSIZE);
      memcpy((char *)matval, (char *)elements, num_elements * DSIZE);
      if (is_userind_in_order == TRUE) {
         memcpy((char*)matind, (char *)indices, num_elements * ISIZE);
      } else {
         for (int i2=0; i2<num_elements; i2++) {
            tmp_matind[i2] = vars[indices[i2]]->userind;
         }
         memcpy((char*)matind, (char *)tmp_matind, num_elements * ISIZE);
      }

      qsort_id(matind, matval, num_elements);

      sym_cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;

      sym_cut->deletable = TRUE;

#ifdef COMPILE_IN_LP      
      if(p->bc_level < 1 && p->mip->mip_inf && (generator == CGL_PROBING_GENERATOR ||
						generator == CGL_CLIQUE_GENERATOR ||
						generator == CGL_KNAPSACK_GENERATOR)){
	 
	 double sos_ratio = 1.0*p->mip->mip_inf->binary_sos_row_num/(p->mip->m + 1);
	 
	 if( ((sos_ratio >= 0.9 && p->iter_num < 2) ||
	      (sos_ratio > 0.1 && sos_ratio < 0.9 && p->mip->mip_inf->prob_type == BINARY_TYPE) ||
	      (sos_ratio > 0.5 && sos_ratio < 0.9 && p->mip->mip_inf->prob_type == BIN_CONT_TYPE)) && 
	     p->node_iter_num < 5 && p_cnt < 50){// && cut_size[i] > 2){
	   //sym_cut->deletable = FALSE;
	    p_cnt++;
	 }
      }
#endif      
      if (send_to_pool){
         sym_cut->name = CUT__SEND_TO_CP;
      }else{
         sym_cut->name = CUT__DO_NOT_SEND_TO_CP;
      }	    
      k++;
   }
   *num_cuts = k;
   // TODO: short circuit the copying to row data and si */
   for (i=0; i<num_row_cuts; i++) {
      cutlist->eraseRowCut(0);
   }

   //FREE(hashes);
   //FREE(is_deleted);
   //FREE(accepted_ind);
   //FREE(cut_size);

   /* update statistics */
   p->lp_stat.num_duplicate_cuts += num_duplicate;
   p->lp_stat.num_poor_cuts += num_poor_quality;
   p->lp_stat.num_unviolated_cuts += num_unviolated;
   p->lp_stat.cuts_generated += num_row_cuts;
   if (p->bc_level<1) {
      p->lp_stat.cuts_root   += num_row_cuts;
   }

   switch (generator) {
    case (CGL_PROBING_GENERATOR):
      p->lp_stat.probing_cuts += num_row_cuts;
      if (p->bc_level<1) {
         p->lp_stat.probing_cuts_root += num_row_cuts;
      }
      break;
    case (CGL_CLIQUE_GENERATOR):
      p->lp_stat.clique_cuts += num_row_cuts;
      if (p->bc_level<1) {
         p->lp_stat.clique_cuts_root += num_row_cuts;
      }
      break;
    case (CGL_KNAPSACK_GENERATOR):
      p->lp_stat.knapsack_cuts += num_row_cuts;
      if (p->bc_level<1) {
         p->lp_stat.knapsack_cuts_root += num_row_cuts;
      }
      break;
    case (CGL_GOMORY_GENERATOR):
      p->lp_stat.gomory_cuts += num_row_cuts;
      if (p->bc_level<1) {
         p->lp_stat.gomory_cuts_root += num_row_cuts;
      }
      break;
    case (CGL_TWOMIR_GENERATOR):
      p->lp_stat.twomir_cuts += num_row_cuts;
      if (p->bc_level<1) {
         p->lp_stat.twomir_cuts_root += num_row_cuts;
      }
      break;
    case (CGL_FLOWCOVER_GENERATOR):
      p->lp_stat.flowcover_cuts += num_row_cuts;
      if (p->bc_level<1) {
         p->lp_stat.flowcover_cuts_root += num_row_cuts;
      }
      break;
    case (CGL_ODDHOLE_GENERATOR):
      p->lp_stat.oddhole_cuts += num_row_cuts;
      if (p->bc_level<1) {
         p->lp_stat.oddhole_cuts_root += num_row_cuts;
      }
      break;
   }

   cut_time = used_time(&total_time);
   p->comp_times.dupes_and_bad_coeffs_in_cuts += cut_time;
        
   return 0;
}
#endif
/*===========================================================================*/
int add_cut_to_mip_inf(lp_prob *p, int cut_n, int *cut_ind, double *cut_val, double cut_rhs, char cut_sense){

   MIPinfo *mip_inf = p->mip->mip_inf; 
   int alloc_size = mip_inf->c_alloc_size; 
   int alloc_num = mip_inf->c_alloc_num; 
   //int t_nz = 0;//mip_inf->c_nz; 
   if(alloc_size < 1){
      alloc_size = MAX(100*cut_n, (int)(100.0*p->lp_data->nz/p->lp_data->m));
      alloc_num = 1000;
      
      mip_inf->c_ind = (int *)malloc(ISIZE*alloc_size);
      mip_inf->c_beg = (int *)malloc(ISIZE*(alloc_num + 1));
      mip_inf->c_val = (double *)malloc(DSIZE*alloc_size);
      mip_inf->c_sense = (char *)malloc(CSIZE*alloc_num);
      mip_inf->c_rhs = (double *)malloc(DSIZE*alloc_num);	    
      mip_inf->c_tmp = (int *)malloc(ISIZE*alloc_num);
      
      mip_inf->c_alloc_size = alloc_size;
      mip_inf->c_alloc_num = alloc_num; 
      mip_inf->c_beg[0] = 0;
   }else{      
      if(alloc_size < mip_inf->c_beg[mip_inf->c_num] + cut_n){
	 alloc_size += MAX(10*cut_n, (int)(10.0*p->lp_data->nz/p->lp_data->m));
	 mip_inf->c_ind = (int *)realloc(mip_inf->c_ind, ISIZE*alloc_size);	       
	 mip_inf->c_val = (double *)realloc(mip_inf->c_val, DSIZE*alloc_size);
	 mip_inf->c_alloc_size = alloc_size;
      }
      if(mip_inf->c_num >= alloc_num){
	 alloc_num += 1000;
	 mip_inf->c_beg = (int *)realloc(mip_inf->c_beg, ISIZE*(alloc_num + 1));
	 mip_inf->c_sense = (char *)realloc(mip_inf->c_sense, CSIZE*alloc_num);
	 mip_inf->c_rhs = (double *)realloc(mip_inf->c_rhs, DSIZE*alloc_num);
	 mip_inf->c_tmp = (int *)realloc(mip_inf->c_tmp, ISIZE*alloc_num);
	       
	 mip_inf->c_alloc_num = alloc_num; 
      }
   }

   int *t_ind = mip_inf->c_ind;
   double *t_var = mip_inf->c_val;
   int *t_beg = mip_inf->c_beg;
   char *t_sense = mip_inf->c_sense;
   double *t_rhs = mip_inf->c_rhs; 
   int t_num = mip_inf->c_num;
   //t_num++;
   
   for (int el_num=0, t_loc = t_beg[t_num]; el_num<cut_n; el_num++, t_loc++) {
      t_ind[t_loc] = cut_ind[el_num];
      t_var[t_loc] = cut_val[el_num];
   }      

   t_beg[t_num + 1] = t_beg[t_num] + cut_n;   
   t_sense[t_num] = cut_sense;
   t_rhs[t_num] = cut_rhs;
   //t_num++;
   (mip_inf->c_num)++;   
      
   return 0;
}

/*===========================================================================*/
#ifdef USE_CGL_CUTS
int add_col_cuts(lp_prob *p, OsiCuts *cutlist, int *bound_changes)
{
   int i, j;
   OsiColCut    col_cut;
   const int verbosity = p->par.verbosity;
   int *indices;
   double *elements;
   double newb;
   int num_col_cuts;
   LPdata       *lp_data = p->lp_data;
   var_desc **vars = lp_data->vars;
   const double big_bound = 1e25;

   num_col_cuts = cutlist->sizeColCuts();
   for (i=0; i<num_col_cuts; i++) {
      col_cut = cutlist->colCut(i);
      if (verbosity>10) {
         col_cut.print();
      }
      indices  = const_cast<int *>(col_cut.lbs().getIndices());
      elements = const_cast<double *>(col_cut.lbs().getElements());
      for (j=0;j<col_cut.lbs().getNumElements();j++) {
         newb = elements[j];
         if (newb > big_bound) {
            newb = big_bound;
         } else if (newb < -big_bound) {
            newb = -big_bound;
         }
         if (vars[indices[j]]->new_lb < newb) {
            vars[indices[j]]->new_lb = newb;
            change_lbub(lp_data, indices[j], newb, vars[indices[j]]->new_ub);
            (*bound_changes)++;
         }
      }
      indices  = const_cast<int *>(col_cut.ubs().getIndices());
      elements = const_cast<double *>(col_cut.ubs().getElements());
      for (j=0;j<col_cut.ubs().getNumElements();j++) {
         newb = elements[j];
         if (newb > big_bound) {
            newb = big_bound;
         } else if (newb < -big_bound) {
            newb = -big_bound;
         }
         if (vars[indices[j]]->new_ub > newb) {
            vars[indices[j]]->new_ub = newb;
            change_lbub(lp_data, indices[j], vars[indices[j]]->new_lb, newb);
            (*bound_changes)++;
         }
      }
   }


   
   for (i=0; i<num_col_cuts; i++) {
      cutlist->eraseColCut(0);
   }

   return 0;
}
#endif
/*===========================================================================*/
int should_stop_adding_cgl_cuts(lp_prob *p, int i, int *should_stop)
{
   *should_stop = FALSE;
   return 0;
}

/*===========================================================================*/
int update_pcost(lp_prob *p)
{
#ifdef COMPILE_IN_LP
   bc_node *parent = p->tm->active_nodes[p->proc_index]->parent;
   char sense = parent->bobj.sense[0];
   int branch_var = parent->bobj.position;
   double *pcost_down = p->pcost_down;
   double *pcost_up = p->pcost_up;
   int *br_rel_down = p->br_rel_down;
   int *br_rel_up = p->br_rel_up;
   double objval = p->lp_data->objval;
   double oldobjval = p->tm->active_nodes[p->proc_index]->lower_bound;
   double oldx =  parent->bobj.value;
   double *x;

   if(parent->bobj.type == SOS1_IMPLICIT){
      return 0;
   }
   
   //get_x(p->lp_data);
   x = p->lp_data->x;
   if (parent->children[0]->bc_index != p->bc_index) {
      sense = (sense == 'L') ? 'G' : 'L';
   }
   if (sense == 'L') {
      if (oldx - x[branch_var] > 1e-5) {
         pcost_down[branch_var] = (pcost_down[branch_var]*
               br_rel_down[branch_var] + (objval - oldobjval)/
               (oldx-x[branch_var]))/(br_rel_down[branch_var] + 1);
         //printf("new pcost_down[%d] = %f\n", branch_var, pcost_down[branch_var]);
         br_rel_down[branch_var]++;
      } else {
         PRINT(p->par.verbosity, 0, ("warning: poor lpetol used while branching\n"));
      }
   } else {
      if (x[branch_var] - oldx > 1e-5) {
         pcost_up[branch_var] = (pcost_up[branch_var]*
               br_rel_up[branch_var] + (objval - oldobjval)/
               (x[branch_var]-oldx))/(br_rel_up[branch_var] + 1);
         //printf("new pcost_up[%d] = %f\n", branch_var, pcost_up[branch_var]);
         br_rel_up[branch_var]++;
      } else {
         PRINT(p->par.verbosity, 0, ("warning: poor lpetol used while branching\n"));
      }
   }

   p->lp_stat.avg_br_obj_impr_in_path = ((p->bc_level-1)*
         p->lp_stat.avg_br_obj_impr_in_path + objval - oldobjval)/p->bc_level;
#endif
   return 0;
}
/*===========================================================================*/

/* check if lb <= ub for each variable. otherwise fathom this branch. */
int check_bounds(lp_prob *p, int *termcode)
{
   int i;
   double *lb, *ub;
   const double lpetol = p->lp_data->lpetol;
   const int n = p->lp_data->n;
   LPdata *lp_data = p->lp_data;
   
   get_bounds(lp_data);
   lb = lp_data->lb;
   ub = lp_data->ub;

   for (i=0; i<n; i++) {
      if (lb[i] > ub[i]+lpetol) {
         break;
      }
   }
   if (i<n) {
      *termcode = LP_D_UNBOUNDED;
   }
   return 0;
}
/*===========================================================================*/
/*===========================================================================*/
