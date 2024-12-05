/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2007 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <memory.h>

/* SYMPHONY include files */
#include "sym_types.h"
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_qsort.h"

/* SPP include files */
#include "spp_constants.h"
#include "spp_types.h"
#include "spp_common.h"
#include "spp_lp.h"
#include "spp_lp_functions.h"


/*****************************************************************************/

void spp_init_lp(spp_lp_problem *spp)
{
   int *matbeg = spp->cmatrix->matbeg;
   int rownum = spp->cmatrix->rownum;
   int colnum = spp->cmatrix->colnum;
   int nzbd = 0;   /* upper bound on the number of nonzeros in atilde */
   int i, len;
   
   spp->tmp = (spp_lp_tmp *) malloc(sizeof(spp_lp_tmp));
   spp->tmp->ctmp_2nD = (char *) malloc(2 * colnum * DSIZE);
   spp->tmp->dtmp_m = (double *) malloc(rownum * DSIZE);
   spp->tmp->dtmp_n = (double *) malloc(colnum * DSIZE);
   spp->tmp->itmp_m = (int *) malloc(rownum * ISIZE);
   spp->tmp->itmp_2n = (int *) malloc(colnum * 2 * ISIZE);

   if (spp->par->which_atilde == COLS_OF_A ||
       spp->par->which_atilde == SPARS_PATTERN) {
      /* compute nzbd = rownum * length of longest column in A */
      for (i = spp->cmatrix->colnum - 1; i >= 0; i--) {
	 len = matbeg[i+1] - matbeg[i];
	 if (len > nzbd) nzbd = len;
      }
      nzbd = nzbd * rownum;
   } else if (spp->par->which_atilde == EDGE_NODE_INC ||
	      spp->par->which_atilde == EDGE_NODE_INC_PERT) {
      /* at most rownum^2/2 edges in graph, two 1's for each edge in the
	 matrix */
      nzbd = rownum * rownum;
   }
}

/*****************************************************************************/

void spp_free_lp_tmp(spp_lp_problem *spp)
{
   FREE(spp->tmp->ctmp_2nD);
   FREE(spp->tmp->dtmp_m);
   FREE(spp->tmp->dtmp_n);
   FREE(spp->tmp->itmp_m);
   FREE(spp->tmp->itmp_2n);
}

/*****************************************************************************/

void disp_where_cut_is_from(int from)
{
   switch (from) {
    case CUT_FROM_CG:
      printf("\nCut(s) received from the cut generator\n");
      break;
    case CUT_FROM_CP:
      printf("\nCut(s) received from the cut pool\n");
      break;
    case CUT_FROM_TM:
      printf("\nCut(s) received from the tree manager\n");
      break;
    case CUT_LEFTOVER:
      printf("\nCut(s) leftover from previous lp\n");
      break;
    case CUT_NOT_IN_MATRIX_SLACK:
      printf("\nCut(s) not in matrix and slack\n");
      break;
#if 0
    case CUT_VIOLATED_SLACK:
      printf("\nCut(s) violated and slack\n");
      break;
#endif
   }
}

/*****************************************************************************/
/* Display cuts in the LP. Violation is not displayed if it is -1.           */

void display_cut_in_lp(spp_lp_problem *spp, cut_data *cut, double violation)
{
   int *indices = spp->tmp->itmp_2n;
   double *coefs = spp->tmp->dtmp_n;
   int *colnames = spp->cmatrix->colnames;
   int j, coef_num;

   switch (cut->type) {

    case CLIQUE:
    case CLIQUE_LIFTED:
    case ODD_HOLE:
    case ODD_ANTIHOLE:
      coef_num = cut->size/ISIZE;
      memcpy(indices, cut->coef, coef_num * ISIZE);
      switch (cut->type) {
       case CLIQUE: printf("CLIQUE\n"); break;
       case CLIQUE_LIFTED: printf("CLIQUE_LIFTED\n"); break;
       case ODD_HOLE: printf("ODD_HOLE\n"); break;
       case ODD_ANTIHOLE: printf("ODD_ANTIHOLE\n"); break;
      }
      printf("   Indices (names): ");
      for (j = 0; j < coef_num; j++)
	/* printf("%i  ", indices[j]); */
	printf("%i (%i)  ", indices[j], colnames[indices[j]]);
      printf("\n");
      if (violation == -1) {
	 printf("   type: %i,  num: %i, rhs: %f\n", cut->type, coef_num,
		cut->rhs);
      } else {
	 printf("   type: %i,  num: %i, rhs: %f,  violation: %f\n",
		cut->type, coef_num, cut->rhs, violation);
      }
      break;

    case ODD_HOLE_LIFTED:
      printf("ODD_HOLE_LIFTED\n");
      break;
    case ODD_ANTIHOLE_LIFTED:
      printf("ODD_ANTIHOLE_LIFTED\n");
      break;
      
    case ORTHOCUT:
      /* FIXME! */
      break;
      
    case WHEEL:
    case OTHER_CUT:
      coef_num = cut->size/(ISIZE + DSIZE);
      memcpy(indices, cut->coef, coef_num * ISIZE);
      memcpy(coefs, cut->coef + coef_num * ISIZE, coef_num * DSIZE);
      if (cut->type == WHEEL) {
	 printf("WHEEL\n");
      } else {
	 printf("OTHER CUT\n");
      }
      printf("   Indices (names) [coefs]: ");
      for (j = 0; j < coef_num; j++)
	 printf("%i (%i) [%f]  ", indices[j], colnames[indices[j]], coefs[j]);
      printf("\n");
      if (violation == -1) {
	 printf("   type: %i,  num: %i, rhs: %f\n", cut->type, coef_num,
		cut->rhs);
      } else {
	 printf("   type: %i,  num: %i, rhs: %f,  violation: %f\n",
		cut->type, coef_num, cut->rhs, violation);
      }
      break;

    default:
      printf("ERROR: Unrecognized cut type in display_cut_in_lp! \n");
      break;
   }
}

/*****************************************************************************/
/*===========================================================================*
 * Convert the cut into a row. Space is allocated for matind and matval here.
 * If the base variables are not all the variables, the part currently
 * commented out must be used.
 *
 * IN: spp, n, vars, cut. OUT: pnzcnt, pmatind, pmatval.
 *===========================================================================*/

void cut_to_row(spp_lp_problem *spp, int n, var_desc **vars, cut_data *cut,
		int *pnzcnt, int **pmatind, double **pmatval)
{
   int *matind;
   double *matval;
   int i, nzcnt, coef_num, oh_num, hub_num;

   switch (cut->type) {

    case CLIQUE:
    case CLIQUE_LIFTED:
    case ODD_HOLE:
    case ODD_ANTIHOLE:
      coef_num = nzcnt = cut->size/ISIZE;
      matind = (int *) malloc(coef_num * ISIZE);
      matval = (double *) malloc(coef_num * DSIZE);
      memcpy(matind, cut->coef, coef_num * ISIZE);
      for (i = coef_num-1; i >= 0; i--)
	 matval[i] = 1.0;
      break;

    case ORTHOCUT:
    case WHEEL:
    case OTHER_CUT:
      if (cut->type == ORTHOCUT)
	 coef_num = nzcnt =
	    (cut->size-spp->cmatrix->rownum*DSIZE) / (ISIZE + DSIZE);
      else
	 coef_num = nzcnt = cut->size / (ISIZE + DSIZE);
      matind = (int *) malloc(coef_num * ISIZE);
      matval = (double *) malloc(coef_num * DSIZE);
      memcpy(matind, cut->coef, coef_num * ISIZE);
      memcpy(matval, cut->coef + coef_num * ISIZE, coef_num * DSIZE);
      break;

    case ODD_HOLE_LIFTED:
    case ODD_ANTIHOLE_LIFTED:
      memcpy(&oh_num, cut->coef, ISIZE);
      memcpy(&hub_num, cut->coef + ISIZE, ISIZE);
      coef_num = nzcnt = oh_num + hub_num;
      matind = (int *) malloc(coef_num * ISIZE);
      matval = (double *) malloc(coef_num * DSIZE);
      memcpy(matind, cut->coef + 2 * ISIZE, coef_num * ISIZE);
      for (i = oh_num-1; i >= 0; i--)
	 matval[i] = 1.0;
      memcpy(matval + oh_num, cut->coef + (2+coef_num)*ISIZE, hub_num * DSIZE);
      break;
      
    default:
      printf("ERROR: Unrecognized cut type in cut_to_row (%i)\n", cut->type);
      break;
   }

#if 0
   /* This is how the routine should look like if not all variables are
      base variables. matind will contain those variable indices that are
      both in vars and the cut. */
   int *indices = spp->tmp->itmp_n;
   double *coefs = spp->tmp->dtmp_n;

   switch (cut->type) {

    case CLIQUE:
    case CLIQUE_LIFTED:
    case ODD_HOLE:
    case ODD_ANTIHOLE:
      coef_num = cut->size/ISIZE;
      matind = (int *) malloc(coef_num * ISIZE);
      matval = (double *) malloc(coef_num * DSIZE);
      memcpy(indices, cut->coef, coef_num * ISIZE);
      /* i runs thru vars, j runs thru indices, nzcnt runs thru matind */
      for (i = j = nzcnt = 0; i < n && j < coef_num; ) {
	 if (vars[i]->userind == indices[j]) {
	    matind[nzcnt] = i;  /* matind is filled wrt position in vars */
	    matval[nzcnt++] = 1;
	    i++; j++;
	 } else if (vars[i]->userind < indices[j]) {
	    i++;
	 } else {
	    j++;
	 }
      }
      break;

    case ORTHOCUT:
    case WHEEL:
    case OTHER_CUT:
      if (cut->type == ORTHOCUT)
	 coef_num = (cut->size-spp->cmatrix->rownum*DSIZE) / (ISIZE + DSIZE);
      else
	 coef_num = cut->size / (ISIZE + DSIZE);
      matind = (int *) malloc(coef_num * ISIZE);
      matval = (double *) malloc(coef_num * DSIZE);
      memcpy(indices, cut->coef, coef_num * ISIZE);
      memcpy(coefs, cut->coef + coef_num * ISIZE, coef_num * DSIZE);
      /* i runs thru vars, j runs thru indices, nzcnt runs thru matind */
      for (i = j = nzcnt = 0; i < n && j < coef_num; ) {
	 if (vars[i]->userind == indices[j]) {
	    matind[nzcnt] = i;  /* matind is filled wrt position in vars */
	    matval[nzcnt++] = coefs[j];
	    i++; j++;
	 } else if (vars[i]->userind < indices[j]) {
	    i++;
	 } else {
	    j++;
	 }
      }
      break;

    default:
      printf("ERROR: Unrecognized cut type in cut_to_row (%i)\n", cut->type);
      break;
   }
#endif
   
   *pnzcnt = nzcnt;
   *pmatind = matind;
   *pmatval = matval;
}

/*****************************************************************************/
/*===========================================================================*
 * Lift cuts. 
 *
 * Note: Only cliques are lifted rigth now.
 *       Cliques are lifted only if they come from the cut generator
 *          (since all variables are always in the formulation, it is
 *           unlikely that a lifted clique can be extended further).
 *
 * Algo for computing dj threshold: take the smallest of
 *    spp->par->lp_dj_threshold_abs and ..->lp_dj_threshold_frac * gap
 *    (if both > 0), lpetol if both are <= 0, and the positive of the two
 *    if only one of them is positive. 
 *===========================================================================*/

/* Needed to get access to the LP problem data structure */
#include "sym_lp.h"

void lift_cut_in_lp(spp_lp_problem *spp, int from, int n,
		    var_desc **vars, cut_data **cut, int *plifted_cutnum,
		    cut_data ***plifted_cuts)
{
   /* FIXME: This function is temporarily broken. */
   lp_prob *p; /* = get_lp_ptr(NULL); */
   double lpetol = p->lp_data->lpetol;
   double *dj = p->lp_data->dj;
   double thres1, thres2, thres, gap, ub;
   spp_lp_params *par = spp->par;
   char *coef = spp->tmp->ctmp_2nD;
   char *new_coef;
   cut_data *new_cut;
   
   if ((*cut)->type == CLIQUE && from == CUT_FROM_CG) {
      /* compute threshold for dj */
      if (p->has_ub)
	 ub = p->ub;
      else
	 ub = 0;
      /* gap is negative if ub is 0 ==> thres1 will be negative */
      gap = p->ub - par->granularity - p->lp_data->objval + lpetol;
      thres1 = gap * par->lp_dj_threshold_frac;
      thres2 = par->lp_dj_threshold_abs;
      if (thres1 > 0 && thres2 > 0)
	 thres = MIN(thres1, thres2);
      else if (thres1 <= 0 && thres2 <= 0)
	 thres = lpetol;
      else
	 thres = MAX(thres1, thres2);
      /* allocate space for new cut */
      new_cut = (cut_data *) malloc(sizeof(cut_data));
      new_cut->coef = coef;
      /* strategy: DONT_CHAGE_CUT since all vars are base vars
         lift clique returns true if lifting was successful, false ow */ 
      if (lift_clique(spp, n, vars, dj, thres, *cut, new_cut,
		      DONT_CHANGE_CUT)) {
	 new_coef = (char *) malloc(new_cut->size * CSIZE);
	 memcpy(new_coef, new_cut->coef, new_cut->size * CSIZE);
	 new_cut->coef = new_coef;
	 *plifted_cutnum = 1;
	 *plifted_cuts = (cut_data **) malloc(sizeof(cut_data *));
	 **plifted_cuts = new_cut;
	 *cut = NULL;
      } else {
	 /* return the same cut */
	 *plifted_cutnum = 1;
	 *plifted_cuts = (cut_data **) malloc(sizeof(cut_data *));
	 **plifted_cuts = *cut;
	 *cut = NULL;
      }
   } else {
      /* return the same cut */
      *plifted_cutnum = 1;
      *plifted_cuts = (cut_data **) malloc(sizeof(cut_data *));
      **plifted_cuts = *cut;
      *cut = NULL;
   }
}

/*****************************************************************************/
/*===========================================================================*
 *===========================================================================*/



/*****************************************************************************/
/* the following are functions invoked during lifting in user_unpack_cuts    */
/*****************************************************************************/

/*===========================================================================*
 * Given a clique with indices cl_indices, extend it with variables in
 * indices in a greedy fashion. Return the number of variables that
 * have been added to the clique. Overwrite indices to have these
 * variables at the beginning of the array.
 *===========================================================================*/

int extend_clique_greedily(col_ordered *cmatrix, int cl_length,
			   int *cl_indices, int length, int *indices)
{
   int i, j, var;
   int pos = 0;  /* pos after the last var that has been added to the clique */

   for (j = 0; j < length; j++) {
      var = indices[j];
      for (i = cl_length - 1; i >= 0; i--)
	 if (spp_is_orthogonal(cmatrix, cl_indices[i], var))
	    break;
      if (i >= 0)
	 continue;
      for (i = pos - 1; i >= 0; i--)
	 if (spp_is_orthogonal(cmatrix, indices[i], var))
	    break;
      if (i < 0)
	 indices[pos++] = var;
   }
   return(pos);
}

/*****************************************************************************/

/*===========================================================================*
 * Lift the clique given in cut. The lifted clique will be in new_cut.
 * new_cut is already allocated (with enough space in coef).
 *
 * Variables in the current formulation are given in vars, their respective
 * reduced costs in dj. Variables with reduced costs greater than
 * dj_threshold are not considered for lifting.
 * Returns TRUE if lifting was successful (that is, managed to add variables
 * to the clique) and FALSE ow. new_cut contains the lifted clique if the
 * return value is TRUE, ow new_cut is junk.
 *
 * strategy indicates whether variables with not sufficiently small reduced
 * costs in the original clique can be thrown out from the clique. (if
 * clique comes from CP, variables in clique might not be all in the basis)
 * possible values for strategy: MAY_CHANGE_CUT, DONT_CHANGE_CUT.
 * algo: if some variable is in cl but not in ind: throw it out from cl.
 * if it is in both: throw it out from ind. if it is in ind but not in cl:
 * leave it in ind.
 *===========================================================================*/

char lift_clique(spp_lp_problem *spp, int n, var_desc **vars, double *dj,
		 double dj_threshold, cut_data *cut, cut_data *new_cut,
		 int strategy)
{
   int i, j, k, length, cl_length, ind, pos_cl, pos_ind;
   int *cl_indices = spp->tmp->itmp_2n;
   int *indices = spp->tmp->itmp_2n + spp->cmatrix->colnum;

   printf("\nLifting the following clique:\n");
   display_cut_in_lp(spp, cut, -1);
   
   cl_length = cut->size/ISIZE;
   memcpy(cl_indices, cut->coef, cl_length * ISIZE);

   /* extract user indices of variables with small enough reduced costs
      and fill them into indices */
   for (i = n - 1, length = 0; i >= 0; i--)
      if (dj[i] < dj_threshold)
	 indices[length++] = vars[i]->userind;
   if (length == 0) {
      printf("... no vars with small enough reduced cost (threshold: %f)\n",
	     dj_threshold);
      return(FALSE);
   }

   /* order indices */
   qsort_i(indices, length);

   if (strategy == MAY_CHANGE_CUT) {
      for (i = 0, j = 0, pos_ind = 0, pos_cl = 0; i<length && j<cl_length; )
	 if (indices[i] < cl_indices[j]) {
	    indices[pos_ind++] = indices[i];
	    i++;
	 } else if (indices[i] == cl_indices[j]) {
	    i++; j++;
	 } else {
	    cl_indices[pos_cl++] = cl_indices[j];
	    j++;
	 }
      for ( ; i < length; i++)
	 indices[pos_ind++] = indices[i];
      /* if sg is left in cl_indices, it is thrown away: do nothing */
      length = pos_ind; cl_length = pos_cl;
	    
   } else if (strategy == DONT_CHANGE_CUT) {
      for (i = 0, j = 0, pos_ind = 0; i < length && j < cl_length; )
	 if (indices[i] < cl_indices[j]) {
	    indices[pos_ind++] = indices[i];
	    i++;
	 } else if (indices[i] == cl_indices[j]) {
	    i++; j++;
	 } else {
	    j++;
	 }
      for ( ; i < length; i++)
	 indices[pos_ind++] = indices[i];
      length = pos_ind;
      
   } else {
      printf("Bogus strategy in lift_clique, %i", strategy);
      return(FALSE);
   }
   
   if (length == 0) {
      printf("... no vars with small enough reduced cost (threshold: %f)\n",
	     dj_threshold);
      return(FALSE);
   } else {
      printf("... %i vars with small enough reduced cost (threshold: %f)\n",
	     length, dj_threshold);
   }
   
   /* generate a random permutation of the indices */
   for (i = 0; i < length - 1; i++) {
      k = RANDOM() % (length - i);
      ind = indices[i];
      indices[i] = indices[i + k];
      indices[i + k] = ind;
   }

   /* shuffle those vars that extend the clique to the beginning of
      indices */
   length = extend_clique_greedily(spp->cmatrix, cl_length, cl_indices,
				   length, indices);

   /* if no variables extend the clique: return */
   if (length == 0) {
      printf("... no vars can extend the clique\n");
      return(FALSE);
   }

   /* fill out new_cut */
   memcpy(indices + length, cl_indices, cl_length * ISIZE);
   length += cl_length;
   qsort_i(indices, length);

   new_cut->type = CLIQUE_LIFTED;
   new_cut->size = length * ISIZE;
   memcpy(new_cut->coef, indices, length * ISIZE);
   new_cut->rhs = 1;
   new_cut->range = 0;
   new_cut->sense = 'L';
   new_cut->branch = TRUE;   /* ? */
   new_cut->name = CUT__SEND_TO_CP;   /* the cut is globally valid */

   printf("... the lifted clique is:\n");
   display_cut_in_lp(spp, new_cut, -1);

   return(TRUE);
}

