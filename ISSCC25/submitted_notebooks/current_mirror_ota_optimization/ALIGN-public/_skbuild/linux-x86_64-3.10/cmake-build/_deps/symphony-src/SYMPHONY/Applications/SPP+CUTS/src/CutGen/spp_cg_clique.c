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
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* SYMPHONY include files */
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_pack_cut.h"
#include "sym_qsort.h"
#include "sym_cg.h"

/* SPP include files */
#include "spp_constants.h"
#include "spp_types.h"
#include "spp_common.h"
#include "spp_cg.h"
#include "spp_cg_clique.h"

/*****************************************************************************/
/* global variables                                                          */
/* (defined so that the recursive fn has few arguments => faster)            */
/*****************************************************************************/

static cut_data *new_cut;   /* tmp, stores a cut to be sent to the lp */
static int       perm_length;  /* see desc at enumerate_maximal_cliques */
static int      *perm_indices;
static int       length;
static int      *indices;
static char     *label;

static int       del_length;   /* already deleted nodes in star cl method */
static int      *del_indices;

/*****************************************************************************/
/*****************************************************************************/
/*              STAR CLIQUES                                                 */
/*****************************************************************************/
/*****************************************************************************/
/*===========================================================================*
 * tmp arrays used
 * find_violated_star_cliques:
 *     current_indices: itmp_8nodenum
 *     current_props  : dtmp_2nodenum + nodenum
 *     star           :     ...       + 2 * nodenum
 *     star_deg       :     ...       + 3 * nodenum
 *     del_indices    :     ...       + 4 * nodenum
 *     label          : ctmp_2nodenum
 *     new_cut        : cuttmp
 * -> spp_delete_node: no tmp
 * -> enumerate_maximal_cliques:
 *         coef   :  itmp_8nodenum + 7 * nodenum
 *    -> register_and_send_cut:
 *           indices: itmp_8nodenum + 7 * nodenum
 *           coefs  : dtmp_2nodenum
 *       -> extend_clique_on_fgraph:
 *              indices: itmp_8nodenum + 7 * nodenum
 * -> greedy_maximal_clique: no tmp
 *    -> register_and_send_cut
 *===========================================================================*/

/*===========================================================================*
 * Find violated star cliques, a la Hoffman-Padberg.
 *
 * Algorithm: Take min degree node. Check for violated cuts in the subgraph
 * consisting of this node and its neighbors (the "star" of this node).
 * Violated cuts are sent back to the LP and are lifted there. Then delete
 * the node and continue with the now min degree node.
 * 
 * Implementation: Two arrays are defined, one contains the indices the other
 * the degrees of all the nodes still in the graph. If the min degree is 0
 * or 1 then the min degree node can be deleted at once.
 * All cliques are enumerated in v U star(v) if the min degree is smaller
 * than the threshold  par->starcl_degree_threshold, otherwise attemp to
 * find maximal clique greedily.
 * 
 * Note: Indices in current_indices are always kept in increasing order.
 *===========================================================================*/

int find_violated_star_cliques(spp_cg_problem *spp, double etol)
{
   int nodenum = spp->fgraph->nodenum;
   fnode *nodes = spp->fgraph->nodes;
   char *node_node = spp->fgraph->node_node;

   int current_nodenum, v_deg, start;
   int *current_indices = spp->tmp->itmp_8nodenum;
   int *current_degrees = spp->tmp->itmp_8nodenum + nodenum;
   double *current_values = spp->tmp->dtmp_2nodenum + nodenum;
   int v, best_ind, other_node;
   double v_val, star_val;

   int star_length;
   int *star = spp->tmp->itmp_8nodenum + 2 * nodenum;
   int *star_deg = spp->tmp->itmp_8nodenum + 3 * nodenum;

   int i, tmp, cnt1 = 0, cnt2 = 0, cnt3 = 0;
   int clique_cnt_e = 0, clique_cnt_g = 0, clique_cnt;
   int largest_star_size = 0;

   /* initialize global variables */
   new_cut = spp->tmp->cuttmp;
   perm_length = 1;  /* always the node whose star we're evaluating */
   del_length = 0;
   del_indices = spp->tmp->itmp_8nodenum + 4 * nodenum;
   label = spp->tmp->ctmp_2nodenum;

   /* initialize current_nodes, current_degrees and current_values */
   current_nodenum = nodenum;
   for (i = 0; i < nodenum; i++) {
      current_indices[i] = i;
      current_degrees[i] = nodes[i].degree;
      current_values[i] = nodes[i].val;
   }

   /* find first node to be checked */
   best_ind = choose_next_node(spp, current_nodenum, current_indices,
			current_degrees, current_values);
   v = current_indices[best_ind];
   v_deg = current_degrees[best_ind];
   v_val = current_values[best_ind];

   /* while there are nodes left in the graph ... (more precisely, while
      there are at least 3 nodes in the graph) */
   while (current_nodenum > 2) {

      /* if the best node is of degree < 2 then it can be deleted */
      if (v_deg < 2) {
	 del_indices[del_length++] = v;
	 spp_delete_node(spp, best_ind, &current_nodenum, current_indices,
			 current_degrees, current_values);
	 best_ind = choose_next_node(spp, current_nodenum, current_indices,
				     current_degrees, current_values);
	 v = current_indices[best_ind];
	 v_deg = current_degrees[best_ind];
	 v_val = current_values[best_ind];
	 largest_star_size = MAX(largest_star_size, v_deg);
	 continue;
      }

      /* star will contain the indices of v's neighbors (but not v's index) */
      start = nodenum * v;
      star++;
      star_deg++;
      star_val = v_val;
      for (i = 0, star_length = 0; i < current_nodenum; i++) {
	 other_node = current_indices[i];
	 if (node_node[start + other_node]) {
	    star[star_length] = other_node;
	    star_deg[star_length++] = current_degrees[i];
	    star_val += current_values[i];
	 }
      }

      /* quick check: if sum of values for the star does not exceed 1 then
	 there won't be a violated clique in the star */
      if (star_val >= 1 + etol) {
	 /* find maximal violated cliques in star. cliques found here might not
	    be maximal wrt to entire fractional graph, only for the current
	    subset of it (some nodes might be already deleted...) */
	 if (v_deg < spp->par->starcl_degree_threshold) {
	    /* enumerate if v_deg is small enough */
	    for (i = 0; i < star_length; i++)
	       label[i] = FALSE;
	    length = star_length;   /* set global vars */
	    indices = star;
	    perm_indices = &v;
	    clique_cnt_e += enumerate_maximal_cliques(spp, 0, etol);
	    star--;
	    star_deg--;
	    cnt1++;
	 } else {
	    /* greedily find if v_deg is too big */
	    /* order nodes in *decreasing* order of their degrees in star */
	    qsort_ii(star_deg, star, star_length);
	    for (i = star_length / 2 - 1; i >= 0; i--) {
	       tmp = star[i];
	       star[i] = star[star_length - i - 1];
	       star[star_length - i - 1] = tmp;
	    }
	    /* put v to the beginning of star */
	    star--;
	    star_deg--;
	    star[0] = v;
	    star_deg[0] = v_deg;
	    star_length++;
	    /* find maxl clique greedily, including v */
	    clique_cnt_g += greedy_maximal_clique(spp, new_cut, star_length,
						  star, 1, etol);
	    cnt2++;
	 }
      } else {
	 cnt3++;
      }
      /* delete v from current_indices */
      del_indices[del_length++] = v;
      spp_delete_node(spp, best_ind, &current_nodenum, current_indices,
		      current_degrees, current_values);
      best_ind = choose_next_node(spp, current_nodenum, current_indices,
				  current_degrees, current_values);
      v = current_indices[best_ind];
      v_deg = current_degrees[best_ind];
      v_val = current_values[best_ind];
      largest_star_size = MAX(largest_star_size, v_deg);
   }

   clique_cnt = clique_cnt_e + clique_cnt_g;
   printf("\nFound %i new violated cliques with the star-clique method\n",
	  clique_cnt);
   printf("The largest star size was %i (threshold %i)\n",
	  largest_star_size, spp->par->starcl_degree_threshold);
   printf("Enumeration %i times, found %i maxl cliques\n", cnt1, clique_cnt_e);
   printf("Greedy %i times, found %i maxl cliques\n", cnt2, clique_cnt_g);
   printf("Skipped a star b/c of small solution value %i times\n", cnt3);

   if (cnt2 == 0)
      printf("   all cliques have been enumerated\n");
   else
      printf("   not all cliques have been eliminated\n");
   
   return(clique_cnt);
}

/*===========================================================================*/

/*===========================================================================*
 * Delete the node of index del_ind (this index is wrt current_indices) from
 * the list current_indices (current_degrees and current_values) and based on
 * the graph stored in spp->fgraph decrease the degrees of its neighbors.
 *
 * There are at least 3 nodes in the graph when this function is invoked.
 *
 * Note that the node indices in current_indices are in increasing order,
 * and that thins ordering is maintained here.
 *
 * spp: IN, general data structure, contains fgraph.
 * del_ind: IN, the index of the node to be deleted (wrt to current_indices)
 * pcurrent_nodenum: INOUT, pointer to the current number of nodes
 * current_indices: INOUT, array of current node indices
 * current_degrees: INOUT, array of current node degrees, in the dame order
 *                  as in current_indices
 * current_values: INOUT, array of solution values
 *===========================================================================*/

void spp_delete_node(spp_cg_problem *spp, int del_ind, int *pcurrent_nodenum,
		     int *current_indices, int *current_degrees,
		     double *current_values)
{
   char *node_node = spp->fgraph->node_node;
   int current_nodenum = *pcurrent_nodenum;

   int i, start, v;
   v = current_indices[del_ind];

   /* delete the entry corresponding to del_ind from current_indices, 
      current_degrees and current_values */
   i = del_ind;
   memmove((char *)(current_indices+i), (char *)(current_indices+i+1),
	   (current_nodenum-i-1) * ISIZE);
   memmove((char *)(current_degrees+i), (char *)(current_degrees+i+1),
	   (current_nodenum-i-1) * ISIZE);
   memmove((char *)(current_values+i), (char *)(current_values+i+1),
	   (current_nodenum-i-1) * ISIZE);
   current_nodenum--;
   
   /* decrease the degrees of v's neighbors by 1 */
   start = spp->fgraph->nodenum * v;
   for (i = 0; i < current_nodenum; i++)
      if (node_node[start + current_indices[i]])
	 current_degrees[i]--;
   
   *pcurrent_nodenum = current_nodenum;
}

/* returns the index of the "best" node wrt current_indices, etc. */
int choose_next_node(spp_cg_problem *spp, int current_nodenum,
		     int *current_indices, int *current_degrees,
		     double *current_values)
{
   int best, i, best_deg;
   double best_val;

   best = 0;
   best_deg = current_degrees[0];
   best_val = current_values[0];

   switch (spp->par->starcl_which_node) {

    case MIN_DEGREE:
      for (i = 0; i < current_nodenum; i++)
	 if (current_degrees[i] < best_deg) {
	    best = i;
	    best_deg = current_degrees[i];
	 }
      break;

    case MAX_DEGREE:
      for (i = 0; i < current_nodenum; i++)
	 if (current_degrees[i] > best_deg) {
	    best = i;
	    best_deg = current_degrees[i];
	 }
      break;

    case MAX_XJ_MAX_DEG:
      for (i = 0; i < current_nodenum; i++) {
	 if (current_values[i] > best_val) {
	    best = i;
	    best_val = current_values[i];
	    best_deg = current_degrees[i];
	 } else if (current_values[i] == best_val &&
		   current_degrees[i] > best_deg) {
	    best = i;
	    best_deg = current_degrees[i];
	 }
      }
      break;

    default:
      printf("ERROR: bad starcl_which_node (in choose_next_node\n");
      break;
   }

   return(best);
   
}


/*****************************************************************************/
/*****************************************************************************/
/*              ROW CLIQUES                                                  */
/*****************************************************************************/
/*****************************************************************************/
/*===========================================================================*
 * tmp arrays used
 * find_violated_row_cliques:
 *     indices        : itmp_8nodenum
 *     degrees        :    ...        + nodenum
 *     itmp           :    ...        + 2 * nodenum
 *     ctmp           : ctmp_2nodenum
 *     new_cut        : cuttmp
 * -> enumerate_maximal_cliques:
 *         coef   :  itmp_8nodenum + 7 * nodenum
 *    -> register_and_send_cut:
 *           indices: itmp_8nodenum + 7 * nodenum
 *           coefs  : dtmp_2nodenum
 *       -> extend_clique_on_fgraph:
 *              indices: itmp_8nodenum + 7 * nodenum
 * -> greedy_maximal_clique: no tmp
 *    -> register_and_send_cut
 *===========================================================================*/

int find_violated_row_cliques(spp_cg_problem *spp, double etol)
{
   char *node_node = spp->fgraph->node_node;
   fnode *nodes = spp->fgraph->nodes;
   int nodenum = spp->fgraph->nodenum;
   int *rmatbeg = spp->rm_frac->rmatbeg;
   int *rmatind = spp->rm_frac->rmatind;
   int rownum = spp->rm_frac->rownum;
   int *itmp = spp->tmp->itmp_8nodenum + 2 * nodenum;
   int *degrees = spp->tmp->itmp_8nodenum + nodenum;
   char *ctmp = spp->tmp->ctmp_2nodenum;
   int i, j, k, pos, len, clique_count;
   int col;
   int *row;    /* pointer to the row in rmatind */
   int largest_length;  /* length of indices */

   /* initialize global variables */
   new_cut = spp->tmp->cuttmp;
   del_length = 0;
   del_indices = NULL;
   length = 0;
   indices = spp->tmp->itmp_8nodenum;   /* nodes that extend the rowcl */

   /* for each row of the matrix */
   clique_count = 0; largest_length = 0;
   for (j = 0; j < rownum; j++) {

      /* if the row is of zero length, take the next row */
      len = rmatbeg[j+1] - rmatbeg[j];
      if (!len)
	 continue;

      row = rmatind + rmatbeg[j];

      /* copy the row of node_node corresponding to the first column in 'row'
	 into ctmp, and take the AND of this vector with every row of
	 node_node corresponding to the rest of the columns in 'row' to
	 determine those columns that are non-orthog to every column in row */
      memcpy(ctmp, &node_node[row[0] * nodenum], nodenum * CSIZE);
      for (i = 1; i < len; i++) {
	 col = row[i];
	 pos = col * nodenum;  /* starting position of this col in node_node */
	 for (k = 0; k < nodenum; k++)
	    ctmp[k] = ctmp[k] * node_node[pos + k];
      }
      for (k = 0, length = 0; k < nodenum; k++)
	 if (ctmp[k])
	    indices[length++] = k;
      largest_length = MAX(length, largest_length);

      /* if there is anything in indices, enumerate (or greedily find)
	 maximal cliques */
      if (length) {
	 if (length < spp->par->rowcl_degree_threshold) {
	    for (i = 0; i < length; i++)
	       ctmp[i] = FALSE;     /* reuse ctmp as label */
	    perm_length = len;   /* global vars */
	    perm_indices = row;
	    label = ctmp;
	    clique_count += enumerate_maximal_cliques(spp, 0, etol);
	 } else {
	    /* order indices into decreasing order of their degrees and
	       copy first 'row' then 'indices' into itmp */
	    for (i = 0; i < length; i++)
	       degrees[i] = - nodes[indices[i]].degree;
	    qsort_ii(degrees, indices, length);
	    for (i = 0; i < len; i++) itmp[i] = row[i];
	    for (i = 0, k = len; i < length; i++) itmp[k++] = indices[i];
	    clique_count += greedy_maximal_clique(spp, new_cut, k, itmp, len,
						  etol);
	 }
      }
   }
      
   printf("\nFound %i new violated cliques with the row-clique method\n",
	  clique_count);
   printf("The largest admissible number was %i (threshold %i)\n",
	  largest_length, spp->par->rowcl_degree_threshold);
   if (largest_length < spp->par->rowcl_degree_threshold)
      printf("   all row cliques have been enumerated\n");
   else
      printf("   not all row cliques have been eliminated\n");
   
   return(clique_count);
}

/*****************************************************************************/
/*****************************************************************************/
/*  these routines are used both for both clique finding method              */
/*****************************************************************************/
/*****************************************************************************/
/*===========================================================================*
 * Enumerate all maximal cliques on the nodes in indices. Maximal cliques
 * that are violated are sent to the lp. Returns the number of maximal
 * violated cliques found. The algorithm is recursive.
 *
 * spp: IN, contains the graph (fgraph)
 * new_cut: TMP, packed together when a violated cut is found
 * perm_length: IN, the length of perm_indices
 * perm_indices: IN, indices of nodes that MUST be in the clique, these
 *                   nodes are supposed to be connected to all nodes in
 *                   indices
 * length: IN, length of indices and label
 * indices: IN, indices of nodes on which maximal cliques are sought
 * label: INOUT, indicates which nodes are in the clique at the moment (T/F)
 * pos: INOUT, position within indices (and label), nodes up to position
 *             pos in indices are permanently labeled (backtrack cannot
 *             change labels)
 *===========================================================================*/

int enumerate_maximal_cliques(spp_cg_problem *spp, int pos, double etol)
{
   fnode *nodes = spp->fgraph->nodes;
   int nodenum = spp->fgraph->nodenum;
   char *node_node = spp->fgraph->node_node;

   int i, j, k, start, cnt, found;
   int *coef;
   double lhs, violation;

   /* starting from position pos, find the first node in indices that
      can be added to the clique, and label it with TRUE */
   while (pos < length) {
      label[pos] = TRUE;
      start = indices[pos] * nodenum;
      for (j = 0; j < pos; j++)
	 if (label[j] && ! node_node[start + indices[j]]) {
	    label[pos] = FALSE;
	    break;
	 }
      if (label[pos++] == TRUE)
	 break;
   }

   /* found counts the number of maximal violated cliques that have been sent
      to the lp under the current level of recursion */
   found = 0;

   /* if not all nodes are labeled: recurse by setting the last node
      labeled TRUE once to TRUE and once to FALSE;
      otherwise check whether the clique found is maximal and violated */
   if (pos < length) {
      found += enumerate_maximal_cliques(spp, pos, etol);
      label[pos-1] = FALSE;
      found += enumerate_maximal_cliques(spp, pos, etol);
   } else {
      /* check if the clique can be extended on indices */

      /* copy indices of the clique into coef (not user inds, coef is a tmp) */
      coef = spp->tmp->itmp_8nodenum + 7 * nodenum;
      for (j = length - 1, cnt = 0; j >= 0; j--)
	 if (label[j])
	    coef[cnt++] = indices[j];
      if (!cnt)
	 return(found);
      
      /* check if the clique can be extended on indices */
      for (k = length - 1; k >= 0; k--) {
	 if (!label[k]) {
	    start = indices[k] * nodenum;
	    for (i = cnt - 1; i >= 0; i--)
	       if (!node_node[start + coef[i]])
		  break;
	    /* if k can be added to the clique, return */
	    if (i < 0)
	       return(found);
	 }
      }

      /* now the clique is maximal on indices.
	 fill relative indices into coef */
      for (j = 0; j < perm_length; j++)
	 coef[cnt++] = perm_indices[j];
      
      /* check if clique is violated */
      for (j = 0, lhs = 0; j < cnt; j++)
	 lhs += nodes[coef[j]].val;
      if (lhs < 1 + etol)
	 return(found);
      
      /* if clique can be extended on del_indices then it can be
	 discarded */
      for (i = 0; i < del_length; i++) {
	 start = del_indices[i] * nodenum;
	 for (j = cnt - 1; j >= 0; j--)
	    if (!node_node[start + coef[j]])
	       break;
	 /* if del_indices[i] can be added to the clique, return */
	 if (j < 0)
	    return(found);
      }
      /* transform relative indices into user indices and order them */
      for (j = cnt - 1; j >= 0; j--)
	 coef[j] = nodes[coef[j]].ind;
      qsort_i(coef, cnt);
      memcpy(new_cut->coef, coef, cnt * ISIZE);
      new_cut->type = CLIQUE;
      new_cut->size = cnt * ISIZE;
      new_cut->rhs = 1;
      new_cut->range = 0;
      new_cut->sense = 'L';
      
      violation = lhs - 1;
      
      found += register_and_send_cut(spp, new_cut, violation, etol);
   }
   return(found);
}

/*===========================================================================*/

/*===========================================================================*
 * Find a violated clique greedily in the given array of indices, starting
 * from pos. Return the number of violated cliques found (1 or 0).
 * If a violated clique is found it is sent to the LP via the function
 * register_and_send_cut.
 * This routine overwrites the array indices: those variables in the
 * clique will be shuffled to the beginning of the array (after pos).
 *===========================================================================*/

int greedy_maximal_clique(spp_cg_problem *spp, cut_data *new_cut,
			  int length, int *indices, int pos, double etol)
{
   fnode *nodes = spp->fgraph->nodes;
   int nodenum = spp->fgraph->nodenum;
   char *node_node = spp->fgraph->node_node;
   int i, j, var, num, start;
   char is_violated;
   double lhs, violation;
   
   for (j = pos, num = pos; j < length; j++) {
      var = indices[j];
      start = var * nodenum;   /* start of row corresp to var in node_node */
      for (i = num-1; i >= 0; i--)
	 if (!node_node[start + indices[i]])
	    break;
      if (i < 0)
	 indices[num++] = var;
   }

   /* now the first num entries in indices contain the clique */
   /* only cliques of size at least 3 are interesting */
   if (num < 3)
      return(0);

   /* compute lhs */
   for (j = 0, lhs = 0; j < num; j++)
      lhs += nodes[indices[j]].val;

   is_violated = (lhs > 1 + etol) ? TRUE: FALSE;

   if (is_violated) {
      for (j = 0; j < num; j++)
	 indices[j] = nodes[indices[j]].ind;
      qsort_i(indices, num);
      memcpy(new_cut->coef, (char *)indices, num * ISIZE);
      new_cut->type = CLIQUE;
      new_cut->size = num * ISIZE;
      new_cut->rhs = 1;
      new_cut->range = 0;
      new_cut->sense = 'L';
      violation = lhs - 1;

      j = register_and_send_cut(spp, new_cut, violation, etol);
      return(j);
   }

   return(0);
}
