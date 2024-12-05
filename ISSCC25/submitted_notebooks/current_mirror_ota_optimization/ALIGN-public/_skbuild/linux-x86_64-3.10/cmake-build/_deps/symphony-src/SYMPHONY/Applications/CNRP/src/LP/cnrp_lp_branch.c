/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* Capacitated Network Routing Problems.                                     */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#define COMPILING_FOR_LP

/* system include files */
#include <math.h>
#include <stdio.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_qsort.h"
#include "sym_lp_u.h"
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#include "sym_lp.h"
/*___END_EXPERIMENTAL_SECTION___*/

/* CNRP include files */
#include "cnrp_lp.h"
#include "cnrp_macros.h"
#include "cnrp_const.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the LP process related
 * to branching.
\*===========================================================================*/

/*===========================================================================*\
 * This function determines whether to branch. You can eseentially
 * leave this up to SYMPHONY unless there is some compelling reason not to.
\*===========================================================================*/

int user_shall_we_branch(void *user, double lpetol, int cutnum,
			 int slacks_in_matrix_num, cut_data **slacks_im_matrix,
			 int slack_cut_num, cut_data **slack_cuts, int varnum,
			 var_desc **vars, double *x, char *status,
			 int *cand_num, branch_obj ***candidates,
			 int *action)
{
   int i;
   double fracx, lpetol1 = 1 - lpetol;

   cnrp_spec *cnrp = (cnrp_spec *) user;


   for (i = varnum - 1; i >= 0; i--){
      if (vars[i]->is_int){
	 fracx = x[i] - floor(x[i]);
	 if (fracx > lpetol && fracx < lpetol1){
	    break;
	 }
      }
   }

   if(i >= 0 ){
      *action = USER__BRANCH_IF_TAILOFF;
   } else{
      *action = USER__BRANCH_IF_MUST;
   }

#if 0   
   if (cnrp->par.detect_tailoff){
      *action = USER__BRANCH_IF_MUST;
      return(USER_SUCCESS);
   }

   *action = USER__BRANCH_IF_TAILOFF;
#endif

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we select the branching candidates. This can essentially be
 * left to SYMPHONY too using one of the built-in functions, but here, I
 * demonstrate how to branch on cuts, which must be done by the user.
\*===========================================================================*/

int user_select_candidates(void *user, double lpetol, int cutnum,
			   int slacks_in_matrix_num,
			   cut_data **slacks_in_matrix, int slack_cut_num,
			   cut_data **slack_cuts, int varnum, var_desc **vars,
			   double *x, char *status, int *cand_num,
			   branch_obj ***candidates, int *action,
			   int bc_level)

{
   cnrp_spec *cnrp = (cnrp_spec *)user;
   cut_data *cut;  
   branch_obj **cand_list, *can;
   int i, candnum, found_violated = FALSE;
   p_w_l *pwl;
   double left_hand_side, lpetol1 = 1 - lpetol, lpetol5=.95, slack, fracx; 
   waiting_row **new_rows;
   int new_row_num;
   int *userind;
   int sim_cand_num = 0, sc_cand_num = 0;
   int total_edgenum = cnrp->vertnum*(cnrp->vertnum - 1)/2;
   int j, cnt = 0;
   double lim[7] = {.1, .15, .20, .233333, .266667, .3, 1};
   branch_obj *cand;
   
   int *xind = (int *) malloc(varnum * ISIZE);
   double *xval = (double *) calloc(varnum, DSIZE);
   
#if 0
   if (!cnrp->par.branch_on_cuts && cnrp->par.branching_rule == 2)
      /* use the built-in rule */
      return(USER_DEFAULT);
#endif
   
   /* first try the fixed-charge variables */
   for (i = varnum - 1; i >= 0; i--){
      if (vars[i]->is_int){
	 fracx = x[i] - floor(x[i]);
	 if (fracx > lpetol && fracx < lpetol1){
	    xind[cnt] = i;
	    xval[cnt++] = fabs(fracx - .5);
	 }
      }
   }

#ifdef ADD_FLOW_VARS
   if (cnt == 0){
      /* Now try the flow variables */
      for (i = varnum - 1; i >= 0; i--){
	 if (!vars[i]->is_int){
	    fracx = x[i] - floor(x[i]);
	    if (fracx > lpetol && fracx < lpetol1){
	       xind[cnt] = i;
	       xval[cnt++] = fabs(fracx - .5);
	    }
	 }
      }
   }
#endif
   
   qsort_di(xval, xind, cnt);

   for (j = 0, i = 0; i < cnt;){
      if (xval[i] > lim[j]){
	 if (i == 0){
	    j++; continue;
	 }else{
	    break;
	 }
      }else{
	 i++;
      }
   }
   cnt = i;

   *cand_num = cnrp->par.strong_branching_cand_num_max;
   *cand_num = MAX(*cand_num, cnrp->par.strong_branching_cand_num_min);
   *cand_num = MIN(*cand_num, cnt);

   if (!*candidates)
      *candidates = (branch_obj **) malloc(*cand_num * sizeof(branch_obj *));
   for (i=*cand_num-1; i>=0; i--){
      cand = (*candidates)[i] = (branch_obj *) calloc(1, sizeof(branch_obj) );
      cand->type = CANDIDATE_VARIABLE;
      cand->child_num = 2;
      cand->position = xind[i];
      cand->sense[0] = 'L';
      cand->sense[1] = 'G';
      cand->rhs[0] = floor(x[xind[i]]);
      cand->rhs[1] = cand->rhs[0] + 1;
      cand->range[0] = cand->range[1] = 0;
   }
   
   FREE(xind);
   FREE(xval);

   return(USER_SUCCESS);
   
#if 0
#ifdef DIRECTED_X_VARS
   nz = collect_nonzeros(p, x, xind, xval, status);

   for (j = 0; j < nz && xind[j] < total_edgenum; j++);
   for (i = 0; i < nz && xind[i] < total_edgenum; i++){
      for (; j < nz && xind[j] < xind[i] + total_edgenum; j++){
	 if (xind[i] == xind[j] + total_edgenum){
	    xval[i] += xval[j];
	    break;
	 }else{
	    xind[j] -= total_edgenum;
	 }
      }
   }
   for (i = 0; i < nz; i++){
      if (xind[i] < total_edgenum){
	 if ((xval[i] = fabs(xval[i] - floor(xval[i]) - .5)) < .5 - lpetol)
	    cnt++;
      }
   }
   qsort_di(xval, xind, nz);
   
   candnum = cnrp->par.strong_branching_cand_num_max;
   candnum = MAX(candnum, cnrp->par.strong_branching_cand_num_min);
   candnum = MIN(candnum, cnt);
   
   FREE(xind);
   FREE(xval);
#endif
#endif
   
   *cand_num = 0;
   candnum = 0;
   /* allocate also memory for the basic vars */
   *candidates = cand_list = (branch_obj **)
      malloc((varnum + (cnrp->par.branch_on_cuts ?
		       (slacks_in_matrix_num + slack_cut_num) : 0)) *
      sizeof(branch_obj *));
   switch (cnrp->par.branch_on_cuts){
    case TRUE:
      pwl = (p_w_l *) malloc((slacks_in_matrix_num + slack_cut_num)*
			     sizeof(p_w_l));
      userind = (int *) malloc(varnum*ISIZE);
      
      for (i = varnum - 1; i >= 0; i--)
	 userind[i] = vars[i]->userind;
      
      /* First go through the slack cuts and enlist the violated ones */
      for (i = 0; i < slack_cut_num; i++){
	 left_hand_side = compute_lhs(varnum, userind, x, cut = slack_cuts[i],
				      cnrp->vertnum);
	 switch (cut->type){
	  case SUBTOUR_ELIM_SIDE:
	    slack = cut->rhs - left_hand_side;
	    if (slack < -lpetol){/*---------------- This cut became violated */
	       found_violated = TRUE;
	       can = cand_list[candnum++] =
		  (branch_obj *) calloc(1, sizeof(branch_obj));
	       can->type = VIOLATED_SLACK;
	       can->position = i;
	    }else if ((!found_violated) && (slack>lpetol) &&
		      !(cut->sense == 'R' || cut->sense == 'E')){
	       pwl[sc_cand_num].lhs = left_hand_side;
	       pwl[sc_cand_num++].position = i;
	    }
	    break;
	    
	  case SUBTOUR_ELIM_ACROSS:
	    slack = left_hand_side  - cut->rhs;
	    if (slack < -lpetol){/*---------------- This cut became violated */
	       found_violated = TRUE;
	       can = cand_list[candnum++] =
		  (branch_obj *) calloc(1, sizeof(branch_obj));
	       can->type = VIOLATED_SLACK;
	       can->position = i;
	    }else if ((!found_violated) && (slack>lpetol) &&
		      !(cut->sense=='R' || cut->sense=='E')){
	       pwl[sc_cand_num].lhs = left_hand_side;
	       pwl[sc_cand_num++].position = i;
	    }
	    break;
	    
	 default:
	    break;
	 }
      }
      if (found_violated){
	 *cand_num = candnum;
	 FREE(pwl);
	 *action = USER__DO_NOT_BRANCH;
	 return(USER_SUCCESS);
      }
      
      /* now go through the slack rows in the matrix and add the potential
	 candidates to the end of the pos/weight lists */
      for (i = 0; i < slacks_in_matrix_num; i++)
	 if ((cut = slacks_in_matrix[i]) &&
	     (cut->type==SUBTOUR_ELIM_SIDE || cut->type== SUBTOUR_ELIM_ACROSS)
	     && !(cut->sense=='R' || cut->sense=='E')){
	    left_hand_side = compute_lhs(varnum, userind, x, cut,
					 cnrp->vertnum);
	    switch (cut->type){
	     case SUBTOUR_ELIM_SIDE:
	       slack = cut->rhs - left_hand_side;
	       /* if (slack > lpetol && slack < lpetol1){*/
	       if (slack > lpetol ){
		  pwl[sc_cand_num+sim_cand_num].lhs = left_hand_side;
		  pwl[sc_cand_num+sim_cand_num].position = i;
		  sim_cand_num++;    
	       }
	       break;
	       
	     case SUBTOUR_ELIM_ACROSS:
	       slack = left_hand_side - cut->rhs;
	       /* if (slack > lpetol && slack < 2-lpetol){*/
	       if (slack > lpetol ){
		  pwl[sc_cand_num+sim_cand_num].lhs = left_hand_side;
		  pwl[sc_cand_num+sim_cand_num].position = i;
		  sim_cand_num++;
	       }
	       break;
	       
	     default:
	       break;
	    }
	 }
      
      /* set the children's rhs etc */
      for (i = 0 ; i < sc_cand_num + sim_cand_num; i++){
	 can = cand_list[candnum++] =
	    (branch_obj *) calloc(1, sizeof(branch_obj));
	 if (i < sc_cand_num ){
	    can->type = CANDIDATE_CUT_NOT_IN_MATRIX;
	    cut = slack_cuts[can->position = pwl[i].position ];
	    user_unpack_cuts(user, CUT_NOT_IN_MATRIX_SLACK,
			     UNPACK_CUTS_SINGLE, varnum, vars, 1,
			     slack_cuts+can->position, &new_row_num,
			     &new_rows);
	    can->row = *new_rows;
	    cut = can->row->cut;
	    FREE(new_rows);
	 }else{
	    can->type = CANDIDATE_CUT_IN_MATRIX;
	    cut = slacks_in_matrix[can->position = pwl[i].position  ];
	 }
	 can->child_num = 2;
	 can->lhs = pwl[i].lhs;
	 /* no need to allocate these. they are of fixed length
	    can->sense = (char *) malloc(2 * CSIZE);
	    can->rhs = (double *) malloc(2 * DSIZE);
	    can->range = (double *) malloc(2 * DSIZE);
	    */
	 switch (cut->type){
	  case SUBTOUR_ELIM_SIDE:
	    if ((slack = cut->rhs - can->lhs) < lpetol1){ 
	       can->sense[0] = 'E';
	       can->rhs[0] = cut->rhs;
	       can->range[0] = 0;
	       can->branch[0] = DO_NOT_BRANCH_ON_THIS_ROW;
	       can->sense[1] = 'L';
	       can->rhs[1] = cut->rhs - 1;
	       can->range[1] = 0;
	       can->branch[1] = ALLOWED_TO_BRANCH_ON;
	    }else{
	       can->sense[0] = 'R';
	       can->rhs[0] = cut->rhs;
	       can->range[0] = -floor(slack) ;
	       can->branch[0] = DO_NOT_BRANCH_ON_THIS_ROW;
	       can->sense[1] = 'L';
	       can->rhs[1] = cut->rhs - ceil(slack);
	       can->range[1] = 0;
	       can->branch[1] = ALLOWED_TO_BRANCH_ON;
	    }
	    break;
	  case SUBTOUR_ELIM_ACROSS:
	    if ((slack = can->lhs - cut->rhs) < 2-lpetol){
	       can->sense[0] = 'E';
	       can->rhs[0] = cut->rhs;
	       can->range[0] = 0;
	       can->branch[0] = DO_NOT_BRANCH_ON_THIS_ROW;
	       can->sense[1] = 'G';
	       can->rhs[1] = cut->rhs + 2;
	       can->range[1] = 0;
	       can->branch[1] = ALLOWED_TO_BRANCH_ON;
	    }else{
	       can->sense[0] = 'R';
	       can->rhs[0] = cut->rhs;
	       can->range[0] = 2*floor(slack/2);
	       can->branch[0] = DO_NOT_BRANCH_ON_THIS_ROW;
	       can->sense[1] = 'G';
	       can->rhs[1] = cut->rhs + 2*floor(slack/2) +2;
	       can->range[1] = 0;
	       can->branch[1] = ALLOWED_TO_BRANCH_ON;
	    }
	    break;
	 }
      }
      FREE(pwl);
      FREE(userind);
      *cand_num = candnum;
      cand_list = *candidates + *cand_num;

    case FALSE:

      switch (((cnrp_spec *)user)->par.branching_rule){
       case 0:
	 {
	    int *xind = (int *) malloc(varnum*ISIZE);
	    double *xval = (double *) malloc(varnum*DSIZE);
	    int cnt = 0;
	    
	    for (i = varnum-1; i >= 0; i--){
	       fracx = x[i] - floor(x[i]);
	       if (fracx > lpetol && fracx < 1-lpetol){
		  xind[cnt] = i;
		  xval[cnt++] = fabs(fracx - .5);
	       }
	    }
	    qsort_di(xval, xind, cnt);

	    candnum = cnrp->par.strong_branching_cand_num_max -
	       cnrp->par.strong_branching_red_ratio * bc_level;
	    candnum = MAX(candnum, cnrp->par.strong_branching_cand_num_min);
	    candnum = MIN(candnum, cnt);
	    
	    for (i = candnum-1; i >= 0; i--){
	       can=cand_list[i]=(branch_obj *) calloc(1, sizeof(branch_obj));
	       can->type = CANDIDATE_VARIABLE;
	       can->child_num = 2;
	       can->position = xind[i];
	       can->sense[0] = 'L';
	       can->sense[1] = 'G';
	       can->rhs[0] = floor(x[xind[i]]);
	       can->rhs[1] = can->rhs[0] + 1;
	       can->range[0] = can->range[1] = 0;
	    }
	    FREE(xind);
	    FREE(xval);
	 }
       break;
       
       case 1:
	 candnum = 0;
	 for (i = varnum-1; i >= 0; i--){
	    fracx = x[i] - floor(x[i]);
	    if (fracx > lpetol && fracx < lpetol5){
	       can = cand_list[candnum++] =
		  (branch_obj *) calloc(1, sizeof(branch_obj));
	       can->type = CANDIDATE_VARIABLE;
	       can->child_num = 2;
	       can->position = i;
	       can->sense[0] = 'L';
	       can->sense[1] = 'G';
	       can->rhs[0] = floor(x[i]);
	       can->rhs[1] = can->rhs[0] + 1;
	       can->range[0] = can->range[1] = 0;
	    }
	 }
	 break;
	 
       case 2:
	 return(USER__CLOSE_TO_HALF);
      }
      *cand_num += candnum;
      *action = USER__DO_BRANCH;
   }
   return(USER_SUCCESS);
}

/*===========================================================================*/
      
double compute_lhs(int number, int *indices, double *values, cut_data *cut,
		   int vertnum)
{
   char *coef;
   int v0, v1;
   double lhs = 0;
   int i;
 
   switch (cut->type){
    
    case SUBTOUR_ELIM_SIDE:
      coef = (char *)(cut->coef);
      for (i = 0, lhs = 0; i<number; i++){
	 BOTH_ENDS(indices[i], &v1, &v0);
	 if (coef[v0 >> DELETE_POWER] & (1 << (v0 & DELETE_AND)) &&
	     (coef[v1 >> DELETE_POWER]) & (1 << (v1 & DELETE_AND)))
	    lhs += values[i];
	   
      }
      return(lhs);

    case SUBTOUR_ELIM_ACROSS:
      coef = (char *)(cut->coef);
      for (lhs = 0, i = 0; i<number; i++){
	 BOTH_ENDS(indices[i], &v1, &v0);
	 if ((coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1) ^
	     (coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1))
	    lhs += values[i];
      }
      
      return(lhs);
      
    default:
      printf("Cut type's not recognized! \n\n");
      return(0);
   }
}

/*===========================================================================*/

/*===========================================================================*\
 * I wrote my own function to compare candidates. Maybe this should go
 * into SYMPHONY.
\*===========================================================================*/

int user_compare_candidates(void *user, branch_obj *can1, branch_obj *can2,
			    double ub, double granularity,
			    int *which_is_better)
{
   int i, j;
   double low1, low2;
   
   for (i = 1; i >= 0; i--)
      if (can1->termcode[i] == LP_OPT_FEASIBLE ||
	  can1->termcode[i] == LP_OPT_FEASIBLE_BUT_CONTINUE ||
	  can1->termcode[i] == LP_D_OBJLIM ||
	  can1->termcode[i] == LP_D_UNBOUNDED ||
	  (can1->termcode[i] == LP_OPTIMAL && can1->objval[i] > ub - granularity))
	 break;

   for (j = 1; j >= 0; j--)
      if (can2->termcode[j] == LP_OPT_FEASIBLE ||
	  can1->termcode[i] == LP_OPT_FEASIBLE_BUT_CONTINUE ||
	  can2->termcode[j] == LP_D_OBJLIM ||
	  can2->termcode[j] == LP_D_UNBOUNDED ||
	  (can2->termcode[j] == LP_OPTIMAL && can2->objval[j] > ub - granularity))
	 break;

   if (i < 0 && j < 0)
      return(USER_DEFAULT);
      
   if (i < 0 && j > 0){
      *which_is_better = SECOND_CANDIDATE_BETTER;
      return(USER_SUCCESS);
   }

   if (i > 0 && j < 0){
      *which_is_better = FIRST_CANDIDATE_BETTER;
      return(USER_SUCCESS);
   }

   low1 = i ? can1->objval[0] : can1->objval[1];
   low2 = j ? can2->objval[0] : can2->objval[1];

   *which_is_better = low1 > low2 ? FIRST_CANDIDATE_BETTER :
                                    SECOND_CANDIDATE_BETTER;

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * You can let SYMPHONY choose which child to retain. The default is
 * to keep the one with the lower objective function value.
\*===========================================================================*/

int user_select_child(void *user, double ub, branch_obj *can, char *action)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, you can print out a more identifiable description of the
 * branching object than just "variable 51". I print out the end points
 * of the edge if an edge is branched on.
\*===========================================================================*/

int user_print_branch_stat(void *user, branch_obj *can, cut_data *cut,
			   int n, var_desc **vars, char *action)
{
   cnrp_spec *cnrp = (cnrp_spec *)user;
   int v0, v1, i;
   char *coef;
   int total_edgenum = cnrp->vertnum*(cnrp->vertnum - 1)/2;
   
   if (cut){
      switch(cut->type){
       case SUBTOUR_ELIM_SIDE:
	 coef = (char *)(cut->coef);
	 for (i = 0; i < n; i++){
	    BOTH_ENDS(vars[i]->userind, &v1, &v0);
	    if (coef[v0 >> DELETE_POWER] & (1 << (v0 & DELETE_AND)) &&
		(coef[v1 >> DELETE_POWER]) & (1 << (v1 & DELETE_AND)))
	       printf("Edge (%i, %i)\n", v0, v1);
	 }

       case SUBTOUR_ELIM_ACROSS:
         coef = (char *)(cut->coef);
	 for (i = 0; i < n; i++){
	    BOTH_ENDS(vars[i]->userind, &v1, &v0);
	    if ((coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1) ^
		(coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1))
	       printf("Edge (%i, %i)\n", v0, v1);
	 } 
      }
   }else{
      if (vars[can->position]->userind < total_edgenum){
	 BOTH_ENDS(vars[can->position]->userind, &v1, &v0);
      }else if (vars[can->position]->userind < 2*total_edgenum){
	 BOTH_ENDS(vars[can->position]->userind-total_edgenum, &v1, &v0);
      }else{
	 printf("ERROR in branching.../n/n");
      }
      printf("Edge (%i, %i)\n", v0, v1);
   }

   return(USER_SUCCESS);
}
