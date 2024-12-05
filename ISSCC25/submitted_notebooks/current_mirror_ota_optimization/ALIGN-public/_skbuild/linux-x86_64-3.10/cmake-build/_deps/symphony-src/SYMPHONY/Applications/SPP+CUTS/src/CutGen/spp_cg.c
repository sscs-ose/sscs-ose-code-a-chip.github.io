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
#include <memory.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>

/* SYMPHONY include files */
#include "sym_proccomm.h"
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_qsort.h"
#include "sym_cg_u.h"

/* SPP include files */
#include "spp_cg.h"
#include "spp_cg_clique.h"
#include "spp_cg_functions.h"
#include "spp_common.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains user-written functions used by the cut generator
 * process.
\*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must receive all of the data sent from
 * user_send_cg_data() and set up data structures. Note that this function is
 * only called if one of COMPILE_IN_CG, COMPILE_IN_LP, or COMPILE_IN_TM is
 * FALSE. For sequential computation, nothing is needed here.
\*===========================================================================*/

int user_receive_cg_data(void **user, int dg_id)
{
   spp_cg_problem *spp;
   col_ordered *m;
   int colnum, rownum, info;

   spp = (spp_cg_problem *) calloc(1, sizeof(spp_cg_problem));
   *user = spp;

   spp->par = (spp_cg_params *) calloc(1, sizeof(spp_cg_params));
   receive_char_array((char *)spp->par, sizeof(spp_cg_params));
   m = spp->cmatrix = (col_ordered *) calloc(1, sizeof(col_ordered));
   receive_int_array(&m->colnum, 1);
   colnum = m->active_colnum = m->colnum;
   receive_int_array(&m->rownum, 1);
   rownum = m->rownum;
   receive_int_array(&m->nzcnt, 1);
   m->colnames = (int *) malloc(colnum * ISIZE);
   m->col_deleted = (char *) calloc(colnum/BITSPERBYTE + 1, CSIZE); /*calloc!*/
   m->obj = (double *) malloc(colnum * DSIZE);
   m->matbeg = (int *) malloc((colnum + 1) * ISIZE);
   m->matind = (row_ind_type *) malloc(m->nzcnt * sizeof(row_ind_type));
   receive_int_array(m->colnames, colnum);
   receive_dbl_array(m->obj, colnum);
   receive_int_array(m->matbeg, (colnum + 1));
   receive_char_array((char *)m->matind, m->nzcnt * sizeof(row_ind_type));

   spp->max_sol_length = rownum;

   /* allocate space for tmp arrays */
   spp->tmp = (spp_cg_tmp *) calloc(1, sizeof(spp_cg_tmp));
   spp->tmp->itmp_m = (int *) malloc(rownum * ISIZE);
   spp->tmp->istartmp_m = (int **) malloc(rownum * sizeof(int *));
   spp->tmp->cuttmp = (cut_data *) calloc(1, sizeof(cut_data));

   /* initialize cg data structures */
   spp->fgraph = (frac_graph *) calloc(1, sizeof(frac_graph));
   spp->cfgraph = (frac_graph *) calloc(1, sizeof(frac_graph));
   spp->cm_frac = (col_ordered *) calloc(1, sizeof(col_ordered));
   spp->rm_frac = (row_ordered *) calloc(1, sizeof(row_ordered));
   spp->rm_frac->rmatbeg = (int *) malloc((rownum+1) * ISIZE);
   spp->lgraph = (level_graph *) calloc(1, sizeof(level_graph));

   allocate_var_length_structures(spp, spp->max_sol_length);
   
   /* cut collection is a local cut pool that contains the cuts that have
      been sent back to the lp */
   spp->cut_coll = (cut_collection *) calloc(1, sizeof(cut_collection));
   spp->cut_coll->max_size = 1000;
   spp->cut_coll->cuts = (cut_data **) calloc(spp->cut_coll->max_size,
						sizeof(cut_data *));
   spp->cut_coll->violation = (double *)
      malloc(spp->cut_coll->max_size * DSIZE);
   spp->cut_coll->mult = (int *)
      malloc(spp->cut_coll->max_size * ISIZE);

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * If the user wants to fill in a customized routine for sending and receiving
 * the LP solution, it can be done here. For most cases, the default routines
 * are fine.
\*===========================================================================*/

int user_receive_lp_solution_cg(void *user)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Find cuts violated by a particular LP solution. This can be a fairly
 * involved function but the bottom line is that an LP solution comes in
 * and cuts go out. Remember, use the function cg_send_cut() to send cuts out
 * when they are found.
\*===========================================================================*/

int user_find_cuts(void *user, int varnum, int iter_num, int level,
		   int index, double objval, int *indices, double *values,
		   double ub, double etol, int *cutnum, int *alloc_cuts,
		   cut_data ***cuts)
{
   spp_cg_problem *spp = (spp_cg_problem *)user;
   int numcuts = 0;
   int i;

	spp->num_cuts = cutnum;
	spp->alloc_cuts= alloc_cuts;
	spp->cuts = cuts;

   /* reallocate space if needed */
   if (varnum > spp->max_sol_length) {
      spp->max_sol_length = varnum;
      free_var_length_structures(spp);
      allocate_var_length_structures(spp, spp->max_sol_length);
   }

   /* construct the fractional graph, etc. */
   construct_fractional_graph(spp, varnum, indices, values);
   construct_cm_frac(spp);
   construct_rm_frac(spp);
   construct_complement_graph(spp->fgraph, spp->cfgraph);

   /* generate cuts */
   numcuts += find_violated_star_cliques(spp, etol);
   /* numcuts += find_violated_row_cliques(spp); */
   numcuts += find_violated_odd_antiholes(spp, etol);
   numcuts += find_violated_odd_holes(spp, etol);
      
   *cutnum = numcuts;

   /* print stat about cut_coll */
   if (spp->cut_coll) {
      printf("CG: Number of cuts in cut_coll: %i\n", spp->cut_coll->size);
      printf("    Type and multiplicity of cuts:    ");
      for (i = 0; i < spp->cut_coll->size; i++) {
	 printf("[%i, %i]   ", spp->cut_coll->cuts[i]->type,
		spp->cut_coll->mult[i]);
      }
      printf("\n\n");
   }

   /* clean up cut_coll */
   if (spp->cut_coll) {
      for (i = 0; i < spp->cut_coll->size; i++) {
	 FREE(spp->cut_coll->cuts[i]->coef);
	 FREE(spp->cut_coll->cuts[i]);
      }
      spp->cut_coll->size = 0;
   }

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free the user data structure. If the default setup is used with sequential
 * computation, nothing needs to be filled in here.
\*===========================================================================*/

int user_free_cg(void **user)
{
   spp_cg_problem *spp = (spp_cg_problem *)(*user);
   int i;
   
   free_var_length_structures(spp);
   if (spp->tmp) {
      FREE(spp->tmp->cuttmp);
      FREE(spp->tmp->itmp_m);
      FREE(spp->tmp->istartmp_m);
      FREE(spp->tmp);
   }
#if !defined(COMPILE_IN_LP) || !defined(COMPILE_IN_CG)
   FREE(spp->par);
   spp_free_cmatrix(spp->cmatrix);
   FREE(spp->cmatrix);
#endif
   FREE(spp->cm_frac);
   FREE(spp->rm_frac->rmatbeg);
   FREE(spp->rm_frac);
   FREE(spp->fgraph);
   FREE(spp->cfgraph);
   FREE(spp->lgraph);
   if (spp->cut_coll) {
      for (i = 0; i < spp->cut_coll->size; i++) {
	 FREE(spp->cut_coll->cuts[i]->coef);
	 FREE(spp->cut_coll->cuts[i]);
      }
      FREE(spp->cut_coll->cuts);
      FREE(spp->cut_coll->violation);
      FREE(spp->cut_coll->mult);
      FREE(spp->cut_coll);
   }
   FREE(*user);

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This is an undocumented (for now) debugging feature which can allow the user
 * to identify the cut which cuts off a particular known feasible solution.
\*===========================================================================*/

#ifdef CHECK_CUT_VALIDITY
int user_check_validity_of_cut(void *user, cut_data *new_cut)
{
  return(USER_DEFAULT);
}
#endif

/*===========================================================================*/

void allocate_var_length_structures(spp_cg_problem *spp, int max_ln)
{
   int max_nzcnt = max_ln * max_ln;
   int rownum = spp->cmatrix->rownum;

   /* tmp arrays */
   spp->tmp->itmp_8nodenum = (int *) malloc(8 * max_ln * ISIZE);
   spp->tmp->dtmp_2nodenum = (double *) malloc(2 * max_ln * DSIZE);
   spp->tmp->ctmp_2nodenum = (char *) malloc(2 * max_ln * CSIZE);
   spp->tmp->cuttmp->coef = (char *) malloc(max_ln*(ISIZE + DSIZE)+ 2*ISIZE);

   /* cm_frac and rm_frac */
   spp->cm_frac->matbeg = (int *) malloc((max_ln+1) * ISIZE);
   spp->cm_frac->matind = (row_ind_type *)
      malloc(max_ln * rownum * sizeof(row_ind_type));
   spp->rm_frac->rmatind = (int *) malloc(max_ln * rownum * ISIZE);

   /* fgraph */
   spp->fgraph->nodes = (fnode *) malloc(max_ln * sizeof(fnode));
   spp->fgraph->all_nbr = (int *) malloc(max_nzcnt * ISIZE);
   spp->fgraph->all_edgecost = (double *) malloc(max_nzcnt * DSIZE);
   spp->fgraph->node_node = (char *) malloc(max_nzcnt * CSIZE);

   /* cfgraph */
   spp->cfgraph->nodes = (fnode *) malloc(max_ln * sizeof(fnode));
   spp->cfgraph->all_nbr = (int *) malloc(max_nzcnt * ISIZE);
   spp->cfgraph->all_edgecost = (double *) malloc(max_nzcnt * DSIZE);
   spp->cfgraph->node_node = (char *) malloc(max_nzcnt * CSIZE);

   /* lgraph */
   spp->lgraph->lnodes = (int *) malloc(max_ln * ISIZE);
   spp->lgraph->lbeg = (int *) malloc((max_ln + 1) * ISIZE);
   spp->lgraph->level_of_node = (int *) malloc(max_ln * ISIZE);
}

/*===========================================================================*/

void free_var_length_structures(spp_cg_problem *spp)
{
   /* tmp */
   FREE(spp->tmp->itmp_8nodenum);
   FREE(spp->tmp->dtmp_2nodenum);
   FREE(spp->tmp->ctmp_2nodenum);
   FREE(spp->tmp->cuttmp->coef);

   /* cm_frac and rm_frac */
   FREE(spp->cm_frac->matbeg);
   FREE(spp->cm_frac->matind);
   FREE(spp->rm_frac->rmatind);

   /* fgraph */
   FREE(spp->fgraph->nodes);
   FREE(spp->fgraph->all_nbr);
   FREE(spp->fgraph->all_edgecost);
   FREE(spp->fgraph->node_node);

   /* cfgraph */
   FREE(spp->cfgraph->nodes);
   FREE(spp->cfgraph->all_nbr);
   FREE(spp->cfgraph->all_edgecost);
   FREE(spp->cfgraph->node_node);

   /* lgraph */
   FREE(spp->lgraph->lnodes);
   FREE(spp->lgraph->lbeg);
   FREE(spp->lgraph->level_of_node);
}

/*===========================================================================*/

/*===========================================================================*
 * Construct the fractional graph. 'number', 'indices' and 'values' describe
 * the variables at fractional level in the solution. 
 *===========================================================================*/

void construct_fractional_graph(spp_cg_problem *spp, int number,
				int *indices, double *values)
{
   frac_graph *fgraph = spp->fgraph;
   int *all_nbr = spp->fgraph->all_nbr;
   double *all_edgecost = spp->fgraph->all_edgecost;
   fnode *nodes = fgraph->nodes;
   int min_degree, max_degree, min_deg_node, max_deg_node;

   int i, j, total_deg, old_total;

   fgraph->nodenum = number;

   /*========================================================================*
      Construct the adjacency lists (neighbors) of the nodes in fgraph.
      Two nodes are adjacent iff the columns corresponding to them are
      non-orthogonal.
    *========================================================================*/

   for ( i = 0, total_deg = 0; i < number; i++ ) {
      old_total = total_deg;
      for ( j = 0; j < number; j++ ) {
	 if ( j != i &&
	      !spp_is_orthogonal(spp->cmatrix, indices[i], indices[j])) {
	    all_nbr[total_deg] = j;
	    all_edgecost[total_deg++] = 1 - values[i] - values[j];
	 }
      }
      nodes[i].ind = indices[i];
      nodes[i].val = values[i];
      nodes[i].degree = total_deg - old_total;
      nodes[i].nbrs = all_nbr + old_total;
      nodes[i].edgecosts = all_edgecost + old_total;
   }

   fgraph->edgenum = total_deg / 2;
   fgraph->density =  2 * (double)fgraph->edgenum / (number * (number-1));

   /*========================================================================*
     Compute the min and max degree.
    *========================================================================*/
   min_deg_node = 0; max_deg_node = 0;
   min_degree = max_degree = nodes[0].degree;
   for ( i = 0; i < number; i++ ) {
      if ( nodes[i].degree < min_degree ) {
	 min_deg_node = i;
	 min_degree = nodes[i].degree;
      }
      if ( nodes[i].degree > max_degree ) {
	 max_deg_node = i;
	 max_degree = nodes[i].degree;
      }
   }
   fgraph->min_degree = min_degree; fgraph->max_degree = max_degree;
   fgraph->min_deg_node = min_deg_node;
   fgraph->max_deg_node = max_deg_node;
   
   /*========================================================================*
     Now create the node-node incidence matrix of the graph.
    *========================================================================*/
   for ( i = number*number-1; i >=0 ; i-- )
      fgraph->node_node[i] = FALSE;
   for ( i = 0; i < number; i++ )
      for ( j = 0; j < nodes[i].degree; j++ )
	 fgraph->node_node[i * number + nodes[i].nbrs[j]] = TRUE;
   
}

/*===========================================================================*/

/*===========================================================================*
 * Construct the column ordered matrix corresponding to the fractional
 * solution. Only colnum, rownum, nzcnt, matbeg and matind are filled out.
 *
 * Space must be already allocated to cm_frac, matbeg and matind.
 *===========================================================================*/

void construct_cm_frac(spp_cg_problem *spp)
{
   fnode *nodes = spp->fgraph->nodes;
   int *matbeg = spp->cmatrix->matbeg;
   row_ind_type *matind = spp->cmatrix->matind;
   int *mb = spp->cm_frac->matbeg;
   row_ind_type *mi = spp->cm_frac->matind;
   int nodenum = spp->fgraph->nodenum;
   int i, col, len;
   
   for (i = 0, mb[0] = 0; i < nodenum; i++) {
      col = nodes[i].ind;
      len = matbeg[col+1] - matbeg[col];
      memcpy(mi + mb[i], matind + matbeg[col], len * sizeof(row_ind_type));
      mb[i+1] = mb[i] + len;
   }

   spp->cm_frac->colnum = nodenum;
   spp->cm_frac->rownum = spp->cmatrix->rownum;
   spp->cm_frac->nzcnt = mb[nodenum];
}

/*===========================================================================*/

/*===========================================================================*
 * Construct row ordered version of cm_frac.
 * Note: columns in this row ordered matrix are indexed by integers from
 * 0 to fgraph->nodenum-1.
 *
 * Space must be already allocated for rm_frac, rmatbeg and rmatind.
 *===========================================================================*/

void construct_rm_frac(spp_cg_problem *spp)
{
   col_ordered *cm = spp->cm_frac;
   row_ordered *rm = spp->rm_frac;
   
   rm->colnum = cm->colnum;
   rm->rownum = cm->rownum;
   rm->nzcnt = cm->nzcnt;
   spp_column_to_row(cm, rm, spp->tmp->itmp_m, spp->tmp->istartmp_m);
}

/*===========================================================================*/

/*===========================================================================*
 * Construct the complement of the fractional graph.
 *===========================================================================*/

void construct_complement_graph(frac_graph *fgraph, frac_graph *cfgraph)
{
   fnode *nodes = fgraph->nodes;
   fnode *cnodes = cfgraph->nodes;
   char *node_node = cfgraph->node_node;
   int nodenum, edgenum, nminusone, i, j, start, degree;
   double dtmp;

   nodenum = cfgraph->nodenum = fgraph->nodenum;
   nminusone = nodenum - 1;
   edgenum = cfgraph->edgenum = nodenum * nminusone / 2 - fgraph->edgenum;
   cfgraph->density = 1 - fgraph->density;

   /* node_node */
   memcpy(node_node, fgraph->node_node, nodenum * nodenum);
   for (i = nodenum*nodenum-1; i >= 0; i--)
      node_node[i] = 1 - node_node[i];
   for (i = nodenum-1; i >= 0; i--)
      node_node[i*nodenum + i] = 0;
   /* nodes */
   for (i = nodenum-1; i >= 0; i--) {
      cnodes[i].degree = nminusone - nodes[i].degree;
      cnodes[i].ind = nodes[i].ind;
      cnodes[i].val = nodes[i].val;
   }
   cnodes[0].nbrs = cfgraph->all_nbr;
   cnodes[0].edgecosts = cfgraph->all_edgecost;
   for (i = 1; i < nodenum; i++) {
      cnodes[i].nbrs = cnodes[i-1].nbrs + cnodes[i-1].degree;
      cnodes[i].edgecosts = cnodes[i-1].edgecosts + cnodes[i-1].degree;
   }
   for (i = 0; i < nodenum; i++) {
      start = i * nodenum;
      dtmp = 1 - cnodes[i].val;
      for (j = 0, degree = 0; j < nodenum; j++) {
	 if (node_node[start + j]) {
	    cnodes[i].nbrs[degree] = j;
	    cnodes[i].edgecosts[degree++] = dtmp - cnodes[j].val;
	 }
      }
   }
   /* min, max degree nodes */
   cfgraph->min_deg_node = fgraph->max_deg_node;
   cfgraph->min_degree = cnodes[cfgraph->min_deg_node].degree;
   cfgraph->max_deg_node = fgraph->min_deg_node;
   cfgraph->max_degree = cnodes[cfgraph->max_deg_node].degree;
}

/*===========================================================================*/

/*********** root is an index wrt fgraph ********/

void construct_level_graph(frac_graph *fgraph, int root, level_graph *lgraph)
{
   int *lnodes = lgraph->lnodes;
   int *lbeg = lgraph->lbeg;
   int *level_of_node = lgraph->level_of_node;
   int nodenum = fgraph->nodenum;
   fnode *nodes = fgraph->nodes;

   int next_pos = 1;   /* pos in lnodes where the next node can be written */
   int curr_pos = 0;   /* pos of currently examined node in lnodes */
   int curr_lev = 0;   /* current level */
   int u;              /* current node */
   int w;              /* neighbor of u */
   
   int i, j, deg;

   /* nothing is in the level graph initially */
   for (i = 0; i < nodenum; i++) level_of_node[i] = -1; 

   /* first node: root */
   lgraph->root = root;
   lnodes[0] = root;
   level_of_node[root] = 0;
   lbeg[0] = 0;

   while (curr_pos < next_pos) {
      u = lnodes[curr_pos++];
      deg = nodes[u].degree; 
      for (j = 0; j < deg; j++) {
	 w = nodes[u].nbrs[j];
	 if (level_of_node[w] < 0) {
	    lnodes[next_pos++] = w;
	    level_of_node[w] = curr_lev + 1;
	 }
      }
      if (curr_pos < next_pos &&
	  level_of_node[u] < level_of_node[lnodes[curr_pos]])
	 lbeg[++curr_lev] = curr_pos;
   }
   lbeg[++curr_lev] = curr_pos;

   lgraph->lnodenum = curr_pos;
   lgraph->levelnum = curr_lev;
}

/*===========================================================================*/

/*===========================================================================*
 * Compare 'new_cut' that has just been generated to all cuts in the
 * cut collection. If the new cut is not in the collection, and it is
 * violated enough, register it and send it back to the LP. If the cut is
 * in the collection and is stronger than the one in the colection, send
 * it back to the lp. Otherwise don't register or send it.
 * Violation is by how much the new cut violates the current solution.
 *
 * Note: DO NOT FREE new_cut!! Will be done from parent function if needed.
 *
 * Returns 1 if cut has been sent to lp, 0 if not.
 *===========================================================================*/

int register_and_send_cut(spp_cg_problem *spp, cut_data *new_cut,
			  double violation, double etol)
{
   cut_collection *cut_coll = spp->cut_coll;
   cut_data **cuts = cut_coll->cuts;
   int nodenum = spp->fgraph->nodenum;
   int *colnames = spp->cmatrix->colnames;

   int i, j, pos, coef_num, oh_len, hub_len;
   int *indices = spp->tmp->itmp_8nodenum + 7 * nodenum;
   double *coefs = spp->tmp->dtmp_2nodenum;
   char *coef;

   /* check if cut is violated enough. if not, return */
   switch (new_cut->type) {

    case CLIQUE:
      /* try to extend the clique on fgraph, in case it was not maximal.
	 'violation' will increase if cut was not maximal...
      extend_clique_on_fgraph(spp, new_cut, &violation); */

      if (violation < spp->par->min_violation_clique)
	 return 0;
      break;

    case ODD_HOLE:
    case ODD_HOLE_LIFTED:
      if (violation < spp->par->min_violation_oddhole)
	 return 0;
      break;
      
    case ODD_ANTIHOLE:
    case ODD_ANTIHOLE_LIFTED:
      if (violation < spp->par->min_violation_oddantihole)
	 return 0;
      break;

    case WHEEL:
      if (violation < spp->par->min_violation_wheel)
	 return 0;
      break;

    case ORTHOCUT:
      if (violation < spp->par->min_violation_orthocut)
	 return 0;
      break;

    case OTHER_CUT:
      if (violation < spp->par->min_violation_othercut)
	 return 0;
      break;

    default:
      printf("\nUnrecognized cut type! (register_and_send_cut)\n");
      return 0;
      break;
   }      
   
   /* if the cut does not need to be added: return */
   switch (new_cut->type) {

    case CLIQUE:
    case ODD_HOLE:
    case ODD_HOLE_LIFTED:
    case ODD_ANTIHOLE:
    case ODD_ANTIHOLE_LIFTED:
    case ORTHOCUT:
      for (i = cut_coll->size - 1; i >= 0; i--) {
	 if (cuts[i]->type == new_cut->type &&
       	     cuts[i]->size == new_cut->size &&
	     !memcmp(cuts[i]->coef, new_cut->coef, new_cut->size))
	    break;
      }
      break;
      
    case WHEEL:
      for (i = cut_coll->size - 1; i >= 0; i--) {
	 if (cuts[i]->type == WHEEL &&
       	     cuts[i]->size == new_cut->size &&
	     cuts[i]->rhs <= new_cut->rhs + etol &&
	     !memcmp(cuts[i]->coef, new_cut->coef, new_cut->size))
	    break;
      }
      break;
      
    case OTHER_CUT:
      for (i = cut_coll->size - 1; i >= 0; i--) {
	 if (cuts[i]->type == OTHER_CUT &&
       	     cuts[i]->size == new_cut->size &&
	     cuts[i]->sense == new_cut->sense &&
	     !memcmp(cuts[i]->coef, new_cut->coef, new_cut->size))
	    if ((cuts[i]->sense == 'L' && cuts[i]->rhs <= new_cut->rhs+etol) ||
		(cuts[i]->sense == 'G' && cuts[i]->rhs >= new_cut->rhs-etol) ||
		(cuts[i]->sense == 'E' && cuts[i]->rhs <= new_cut->rhs+etol &&
		 cuts[i]->rhs >= new_cut->rhs-etol) ||
		(cuts[i]->sense == 'R' && cuts[i]->rhs >= new_cut->rhs-etol &&
		 cuts[i]->rhs+cuts[i]->range<=new_cut->rhs+new_cut->range+etol)
		)
	       break;
      }
      break;
   }

   /* if cut (or a stronger cut) has been found: return */
   if ( i >= 0 ) {
      cut_coll->mult[i]++;
      return 0;
   }

   /* We get here only if the cut is new... */

   /* store the cut in the collection. allocate more space if needed */
   if (cut_coll->size == cut_coll->max_size) {
      cut_coll->max_size += 500;
      cuts = spp->cut_coll->cuts = (cut_data **)
	 realloc((char *)cuts, cut_coll->max_size * sizeof(cut_data *));
      spp->cut_coll->violation = (double *)
	 realloc((char *)cut_coll->violation, cut_coll->max_size * DSIZE);
      spp->cut_coll->mult = (int *)
	 realloc((char *)cut_coll->mult, cut_coll->max_size * ISIZE);
   }
   pos = cut_coll->size;
   cut_coll->size++;
   /* allocate space for the cut in the collection */
   cuts[pos] = (cut_data *) malloc(sizeof(cut_data));
   *cuts[pos] = *new_cut;
   cuts[pos]->coef = (char *) malloc(new_cut->size);
   memcpy(cuts[pos]->coef, new_cut->coef, new_cut->size);
   cut_coll->violation[pos] = violation;
   cut_coll->mult[pos] = 0;

   /* now we send the cut indexed by 'pos' to the lp */
   cg_add_user_cut(cuts[pos], spp->num_cuts, spp->alloc_cuts, spp->cuts);

   /* for debugging purposes: print out info which cut was sent to the lp */
   switch (cuts[pos]->type) {

    case CLIQUE:
    case ODD_HOLE:
    case ODD_ANTIHOLE:
      coef_num = cuts[pos]->size/ISIZE;
      memcpy(indices, cuts[pos]->coef, coef_num * ISIZE);
      if (cuts[pos]->type == CLIQUE) {
	 printf("\nViolated CLIQUE inequality found\n");
      } else if (cuts[pos]->type == ODD_HOLE) {
	 printf("\nViolated ODD HOLE inequality found\n");
      } else {
	 printf("\nViolated ODD ANTIHOLE inequality found\n");
      }
      printf("   Indices (names): ");
      for ( j = 0; j < coef_num; j++ )
	/* printf("%i  ", indices[j]); */
	printf("%i (%i)  ", indices[j], colnames[indices[j]]);
      printf("\n");
      printf("   type: %i,  num: %i, rhs: %f,  violation: %f\n",
	     cuts[pos]->type, coef_num, cuts[pos]->rhs, violation);
      break;

    case ODD_HOLE_LIFTED:
    case ODD_ANTIHOLE_LIFTED:
      coef = cuts[pos]->coef;
      memcpy(&oh_len, coef, ISIZE);
      memcpy(&hub_len, coef + ISIZE, ISIZE);
      coef_num = oh_len + hub_len;
      memcpy(indices, coef + 2 * ISIZE, coef_num * ISIZE);
      memcpy(coefs, coef + (2+coef_num) * ISIZE, hub_len * DSIZE);
      if (cuts[pos]->type == ODD_HOLE_LIFTED) 
	 printf("\nViolated LIFTED ODD HOLE inequality found\n");
      else
	 printf("\nViolated LIFTED ODD ANTIHOLE inequality found\n");
      printf("   Indices (names) of nodes in odd hole: ");
      for (j = 0; j < oh_len; j++)
	printf("%i (%i)  ", indices[j], colnames[indices[j]]);
      printf("\n");
      printf("   Indices (names) [coefs] of hubs: ");
      for (j = 0; j < hub_len; j++)
	 printf("%i (%i) [%f]  ", indices[oh_len+j],
		colnames[indices[oh_len+j]], coefs[j]);
      printf("\n");
      if (cuts[pos]->type == ODD_HOLE_LIFTED) 
	 printf("   type: %i,  oh_num: %i, hub_num: %i, rhs: %f, violation: %f\n",
		cuts[pos]->type, oh_len, hub_len, cuts[pos]->rhs, violation);
      else
	 printf("   type: %i,  oah_num: %i, hub_num: %i, rhs: %f, violation: %f\n",
		cuts[pos]->type, oh_len, hub_len, cuts[pos]->rhs, violation);
      /* we don't print this cut into the message window right now   FIXME  */
      break;
      
    case ORTHOCUT:
      /* FIXME! */
      break;

    case WHEEL:
    case OTHER_CUT:
      coef_num = cuts[pos]->size/(ISIZE + DSIZE);
      memcpy(indices, cuts[pos]->coef, coef_num * ISIZE);
      memcpy(coefs, cuts[pos]->coef + coef_num * ISIZE, coef_num * DSIZE);
      if (cuts[pos]->type == WHEEL) {
	 printf("\nViolated WHEEL inequality found\n");
      } else {
	 printf("\nViolated OTHER CUT found\n");
      }
      printf("   Indices (names) [coefs]: ");
      for ( j = 0; j < coef_num; j++ )
	 printf("%i (%i) [%f]  ", indices[j], colnames[indices[j]], coefs[j]);
      printf("\n");
      printf("   type: %i,  num: %i, rhs: %f, violation: %f\n",
	     cuts[pos]->type, coef_num, cuts[pos]->rhs, violation);
      break;
   }

   return 1;
}

/*===========================================================================*/

/*===========================================================================*
 * Try to extend a clique on fgraph (greedily).
 *===========================================================================*/

void extend_clique_on_fgraph(spp_cg_problem *spp, cut_data *new_cut,
			     double *pviolation)
{
   int old_coef_num, coef_num, i, j, k;
   double lhs = 1 + *pviolation;
   fnode *nodes = spp->fgraph->nodes;
   int nodenum = spp->fgraph->nodenum;
   int *indices = spp->tmp->itmp_8nodenum + 7 * nodenum;
   /* same tmp array is used in parent fn, but only after this fn returns */
   int userind;
   

   old_coef_num = coef_num = new_cut->size/ISIZE;
   memcpy(indices, new_cut->coef, coef_num * ISIZE);

   /* i runs thru nodes in fgraph, j runs thru nodes in the clique.
      note that the clique is a subgraph of fgraph */
   for ( i = j = 0; i < nodenum && j < old_coef_num; i++ ) {
      userind = nodes[i].ind;
      if ( userind < indices[j] ) {
	 /* check if the node can be added to the clique */
	 for ( k = 0; k < coef_num; k++ )
	    if (spp_is_orthogonal(spp->cmatrix, userind, indices[k]))
	       break;
	 if ( k == coef_num ) {
	    /* node can be added ... */
	    indices[coef_num++] = userind;
	    lhs += nodes[i].val;
	 }
      } else {
	 /* node is in the clique */
	 j++;
      }
   }
   for ( ; i < nodenum; i++ ) {
      userind = nodes[i].ind;
      /* check if the node can be added to the clique */
      for ( k = 0; k < coef_num; k++ )
	 if (spp_is_orthogonal(spp->cmatrix, userind, indices[k]))
	    break;
      if ( k == coef_num ) {
	 /* node can be added ... */
	 indices[coef_num++] = userind;
	 lhs += nodes[i].val;
      }
   }
      
   /* if some nodes were added to the clique ... */
   if (old_coef_num < coef_num) {
      new_cut->size = coef_num * ISIZE;
      qsort_i(indices, coef_num);
      memcpy(new_cut->coef, indices, new_cut->size);
      *pviolation = lhs - 1;
   }
}
   
/*****************************************************************************/
/*****************************************************************************/
/*                            UTILITY                                        */
/*****************************************************************************/
/*****************************************************************************/

/*===========================================================================*
 * Cuts coming from the graph drawing application are given in terms of
 * variable names, not indices. This function changes the names into indices.
 *===========================================================================*/

void translate_cut_to_indices(spp_cg_problem *spp, cut_data *cut)
{
   int *colnames = spp->cmatrix->colnames;
   int colnum = spp->cmatrix->colnum;
   int nodenum = spp->fgraph->nodenum;
   int i, j, name, coef_num;
   int *names = spp->tmp->itmp_8nodenum;
   int *itmp = spp->tmp->itmp_8nodenum + nodenum;

   switch (cut->type) {
    case CLIQUE:
    case ODD_HOLE:
    case ODD_ANTIHOLE:
      coef_num = cut->size/ISIZE;
      break;

    case ORTHOCUT:
    case OTHER_CUT:
      coef_num = cut->size/(ISIZE + DSIZE);
      break;
   }

   memcpy(names, cut->coef, coef_num * ISIZE);
   for (i = 0; i < coef_num; i++) {
      name = names[i];
      for (j = colnum-1; j >=0; j--)
	 if (colnames[j] == name)
	    break;
      if (j >= 0)
	 names[i] = j;
      else
	 printf("ERROR: Variable with name %i is not found\n", name);
   }

   switch (cut->type) {
    case CLIQUE:
    case ORTHOCUT:
    case OTHER_CUT:
      qsort_i(names, coef_num);
      break;

    case ODD_HOLE:
    case ODD_ANTIHOLE:
      /* find smallest indexed node and rotate cycle to have that first */
      rotate_odd_hole(coef_num, names, itmp);
      break;
   }
   
   memcpy(cut->coef, names, coef_num * ISIZE);
}

/*===========================================================================*/

/*===========================================================================*
 * Rotate indices of odd hole so that entry with smallest index is first and
 * smaller indexed neighbor of first node is the second.
 *===========================================================================*/

void rotate_odd_hole(int length, int *indices, int *itmp)
{
   int i, minind, minval, tmp;

   for (i = 1, minval = indices[0], minind = 0; i < length; i++)
      if (indices[i] < minval) {
	 minval = indices[i];
	 minind = i;
      }
   if (indices[(minind-1+length)%length] < indices[(minind+1)%length]) {
      /* reverse cycle */
      for (i = (int)(floor((double)length/2)) - 1; i >= 0; i--) {
	 tmp = indices[i];
	 indices[i] = indices[length - 1 - i];
	 indices[length - 1 - i] = tmp;
      }
      minind = length - 1 - minind;
   }
   if (minind > 0) {
      memcpy(itmp, indices, minind * ISIZE);
      memmove(indices, indices + minind, (length - minind) * ISIZE);
      memcpy(indices + (length - minind), itmp, minind * ISIZE);
   }   
}

