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
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_pack_cut.h"
#include "sym_qsort.h"
#include "sym_cg.h"

/* SPP include files */
#include "spp_constants.h"
#include "spp_types.h"
#include "spp_common.h"
#include "spp_cg.h"
#include "spp_cg_functions.h"

/*****************************************************************************/
/*****************************************************************************/
/*              ODD HOLES                                                    */
/*****************************************************************************/
/*****************************************************************************/
/*===========================================================================*
 * tmp arrays used
 * find_violated_odd_holes:
 *     roots          : itmp_8nodenum
 *     oh             :     ...       + nodenum
 *     hubs           :     ...       + 2 nodenum
 *     hub_coef       :     ...       + 3 nodenum
 *     itmp           :     ...       + 5 nodenum
 *     new_cut        : cuttmp
 * -> find_chordless_oh:
 *        path_u      : itmp_8nodenum + 2 nodenum
 *        path_w      :     ...       + 3 nodenum
 *    -> min_path_to_root:
 *           pred     : itmp_8nodenum + 4 nodenum
 *           reached  :     ...       + 5 nodenum
 *           dist     : dtmp_2nodenum
 * -> rotate_odd_hole: no tmp
 * -> register_and_send_cut:
 *        indices: itmp_8nodenum + 5 nodenum
 *        coefs  : dtmp_2nodenum
 *===========================================================================*/

int find_violated_odd_holes(spp_cg_problem *spp, double etol)
{
   int nodenum = spp->fgraph->nodenum;
   fnode *nodes = spp->fgraph->nodes;
   char *node_node = spp->fgraph->node_node;
   int *lnodes = spp->lgraph->lnodes;
   int *lbeg = spp->lgraph->lbeg;
   int *roots = spp->tmp->itmp_8nodenum;
   int *oh = spp->tmp->itmp_8nodenum + nodenum;
   int *hubs = spp->tmp->itmp_8nodenum + 2 * nodenum;
   int *hub_coef = spp->tmp->itmp_8nodenum + 3 * nodenum;
   int *itmp = spp->tmp->itmp_8nodenum + 7 * nodenum;
   double *dtmp = spp->tmp->dtmp_2nodenum;
   cut_data *new_cut = spp->tmp->cuttmp;
   int begl, endl, levelnum, *coef;
   int i, j, l, cnt, oh_len, hub_len, num_roots, numcuts = 0;
   int u, v, w;
   double prob, choose, lhs_oh, violation, *dcoef;
   
   /* Choose a set of nodes randomly to be the roots (one by one)
      of the bfs tree. Choose 20 to 50 percent of all nodes, depending
      on the density of the graph (the denser the graph, the more nodes we
      choose right now). Should be made a parameter. */
   prob = .2 + .3 * spp->fgraph->density;
   for (i = 0, num_roots = 0; i < nodenum; i++){
      /* choose each node with probability prob */
      choose = (double)RANDOM()/MAXINT;
      if (choose < prob)
	 roots[num_roots++] = i;
   }

   for (i = 0; i < num_roots; i++) {
      v = roots[i];
      /* construct level graph with root v and display it */
      construct_level_graph(spp->fgraph, v, spp->lgraph);
      /* display_level_graph(spp, spp->fgraph); */

      /* for each level >= 2 */
      levelnum = spp->lgraph->levelnum;
      for (l = 2; l < levelnum; l++) {
	 begl = lbeg[l]; endl = lbeg[l+1];
	 /* if there is at most one node on this level: continue */
	 if (endl - begl <= 1)
	    continue;
	 oh_len = 2 * l + 1;

	 /* examine each pair of adjacent nodes on this level.
	    note: u and w are indices wrt lgraph here, so lnodes[u] and
	    lnodes[w] are the indices wrt fgraph!                       */
	 for (u = begl; u < endl - 1; u++) { 
	    for (w = u + 1; w < endl; w++) {
	       /* if the nodes are adjacent try to find paths from u and w
		  to the root (v) */
	       if (node_node[lnodes[u] * nodenum + lnodes[w]]) {
		  lhs_oh = find_chordless_oh(spp, spp->fgraph,
					     lnodes[u], lnodes[w], oh);
		  if (lhs_oh > -1) {
		     if (lhs_oh > l + etol) {
			/* odd hole is violated: send back cut */
			coef = (int *)(dtmp);
			for (j = 0; j < oh_len; j++)
			   coef[j] = nodes[oh[j]].ind;
			rotate_odd_hole(oh_len, coef, itmp);
			memcpy(new_cut->coef, coef, oh_len * ISIZE);
			new_cut->type = ODD_HOLE;
			new_cut->size = oh_len * ISIZE;
			new_cut->rhs = l;
			new_cut->range = 0;
			new_cut->sense = 'L';
			violation = lhs_oh - l;
			numcuts +=
			   register_and_send_cut(spp, new_cut, violation, etol);
		     } else {
			/* odd hole is not violated: try to lift */
			/* display_level_graph(spp, spp->fgraph); */
			lhs_oh =
			   lift_nonviolated_odd_hole(spp, oh_len, oh, lhs_oh,
						     &hub_len, hubs, hub_coef);
			if (lhs_oh > l + etol) {
			   /* lifted odd hole is violated: send back cut */
			   coef = (int *)(dtmp);
			   coef[0] = oh_len;
			   coef[1] = hub_len;
			   for (j = 0, cnt = 2; j < oh_len; j++)
			      coef[cnt++] = nodes[oh[j]].ind;
			   rotate_odd_hole(oh_len, coef + 2, itmp);
			   for (j = 0; j < hub_len; j++)
			      coef[cnt++] = nodes[hubs[j]].ind;
			   memcpy(new_cut->coef, coef, cnt * ISIZE);
			   dcoef = dtmp;
			   for (j = 0; j < hub_len; j++)
			      dcoef[j] = (double) hub_coef[j];
			   memcpy(new_cut->coef + cnt * ISIZE, dcoef,
				  hub_len * DSIZE);
			   new_cut->type = ODD_HOLE_LIFTED;
			   new_cut->size = cnt * ISIZE + hub_len * DSIZE;
			   new_cut->rhs = l;
			   new_cut->range = 0;
			   new_cut->sense = 'L';
			   violation = lhs_oh - l;
			   numcuts +=
			      register_and_send_cut(spp, new_cut, violation,etol);
			}
			/* undisplay_level_graph(spp); */
		     }
		  }
	       } /* endif u, w adjacent */
	    } /* endfor w */
	 } /* endfor u */
	       
      } /* endfor l */

      /* undisplay_level_graph(spp); */
   } /* endfor i */
   return(numcuts);
}

/*===========================================================================*/

/*===========================================================================*
 * Find a chordless odd hole of minimum cost (weights of edges added up
 * along the cycle) that contains u, w, and the root of the level-graph.
 * Returns the value of the lhs for the odd hole, -1 if no odd hole is found.
 *
 * u, w     (IN)  indices of nodes (wrt fgraph) thru which an odd hole is
 *                sought. 
 * oh       (OUT) contains indices of nodes (wrt fgraph) in the odd hole
 *                if one is found (u ... root ... w), garbage ow.
 *===========================================================================*/

double find_chordless_oh(spp_cg_problem *spp, frac_graph *fgraph, int u,
			 int w, int *oh)
{
   int nodenum = fgraph->nodenum;
   fnode *nodes = fgraph->nodes;
   char *node_node = fgraph->node_node;
   int *level_of_node = spp->lgraph->level_of_node;
   int *path_u = spp->tmp->itmp_8nodenum + 2 * nodenum;
   int *path_w = spp->tmp->itmp_8nodenum + 3 * nodenum;
   int *saved_levels = oh;    /* we use oh to temp store the levels of nodes */
   int root = spp->lgraph->root;
   double cost_oh, lhs_oh = -1, cost_path_u = -1, cost_path_w = -1;
   int z;  /* a node index */
   int i, j, l, deg;

   l = level_of_node[u];
   /* find min cost path to the root from u in the level graph */
   min_path_to_root(spp, fgraph, u, path_u, &cost_path_u);
   /* save the levels */
   memcpy(saved_levels, level_of_node, nodenum * ISIZE);
   /* block the nodes on the path from u to the root and their neighbors
      (except for the root) by setting the levels of these nodes to -1 */
   for (i = 0; i < l; i++) {
      z = path_u[i];
      deg = nodes[z].degree;
      level_of_node[z] = -1;
      for (j = 0; j < deg; j++)
	 level_of_node[nodes[z].nbrs[j]] = -1;
   }
   level_of_node[root] = 0;
   /* now the level of w is -1 since it is adjacent to u. w can also be
      adjacent to the second node on the path (the one above u) but not
      to nodes on higher levels b/c of the BFS ordering of the level graph.
      If w is adjacent to the second node, there is a chord, so return.    */
   if (node_node[w * nodenum + path_u[1]]) {
      /* restore levels */
      memcpy(level_of_node, saved_levels, nodenum * ISIZE);
      return(lhs_oh);
   }
   /* restore level of w */
   level_of_node[w] = l;
   /* find min cost path to the root from w in the level graph */
   min_path_to_root(spp, fgraph, w, path_w, &cost_path_w);
   /* restore levels */
   memcpy(level_of_node, saved_levels, nodenum * ISIZE);

   /* if there is a path from w to the root, put together the odd hole
      and compute its cost */
   if (cost_path_w > -1) {
      memcpy(oh, path_u, (l+1) * ISIZE);
      for (i = 1; i <= l; i++)
	 oh[l+i] = path_w[l-i];
      cost_oh = cost_path_u + cost_path_w + 1 - nodes[u].val - nodes[w].val;
      lhs_oh = l + (1 - cost_oh) / 2;
   }
   return(lhs_oh);
}

/*===========================================================================*/

/*===========================================================================*
 * Find a shortest path of length level_of_node[u] from u to the root of
 * the level-graph. Nodes on levels higher than that of u are enumerated
 * in a BFS fashion. If no path exists from u to the root, *pcost is -1.
 *
 * u      (IN)  is the index of the node (wrt fgraph) from where shortest
 *              path to the root is sought,
 * path_u (OUT) contains indices of nodes (wrt fgraph) on the shortest path
 *              from u to the root if one exists, garbage ow.
 * pcost  (OUT) pointer to the cost of the shortest path (to -1 if none found)
 *===========================================================================*/

void min_path_to_root(spp_cg_problem *spp, frac_graph *fgraph, int u,
		      int *path_u, double *pcost)
{
   int nodenum = fgraph->nodenum;
   int root = spp->lgraph->root;
   int *level_of_node = spp->lgraph->level_of_node;
   fnode *nodes = fgraph->nodes;
   int i, pos, nextpos, x, y, level_x;
   /* pred[w] is the predecessor of node w in the level-by-level shortest
              path tree built from u;
      dist[w] is the shortest path distance of w from u in the above tree,
      reached[] contains the indices of nodes already reached, in the order
                they have been reached.                                     */
   int *pred = spp->tmp->itmp_8nodenum + 4 * nodenum;
   double *dist = spp->tmp->dtmp_2nodenum;
   int *reached = spp->tmp->itmp_8nodenum + 5 * nodenum;

   /* initialize */
   for (i = 0; i < nodenum; i++) {
      pred[i] = nodenum;   /* this is a dummy node */
      dist[i] = spp->lgraph->levelnum + 2;   /* obvious ub on dist */
   }

   pred[u] = u;
   dist[u] = 0;
   reached[0] = u;
   pos = 0;
   nextpos = 1;

   while (pos < nextpos) {
      x = reached[pos++];
      level_x = level_of_node[x];
      for (i = 0; i < nodes[x].degree; i++) {
	 y = nodes[x].nbrs[i];
	 if (level_of_node[y] == level_x - 1) {
	    if (pred[y] == nodenum)
	       reached[nextpos++] = y;
	    if (dist[y] > dist[x] + nodes[x].edgecosts[i]) {
	       dist[y] = dist[x] + nodes[x].edgecosts[i];
	       pred[y] = x;
	    }
	 }
      }
   }

   /* if the root has been reached... */
   if (pred[root] < nodenum){
      pos = level_of_node[u];
      path_u[pos--] = root;
      x = pred[root];
      while (x != u){
	 path_u[pos--] = x;
	 x = pred[x];
      }
      path_u[pos] = u;
      *pcost = dist[root];
   }else{
      *pcost = -1;
   }
  
}


/*===========================================================================*/

/* this version is closer to that of HP (each hub candidate is lifted in
 and the best (the one which improves the lhs the most) is chosen. */

double lift_nonviolated_odd_hole(spp_cg_problem *spp, int oh_len, int *oh,
				 double lhs_oh, int *phub_len, int *hubs,
				 int *hub_coef)
{
   int nodenum = spp->fgraph->nodenum;
   fnode *nodes = spp->fgraph->nodes;
   char *node_node = spp->fgraph->node_node;
   int rhs = (oh_len - 1)/2;
   int hub_len = 0;
   int *num_nbrs = spp->tmp->itmp_8nodenum + 4 * nodenum;
   char *label = spp->tmp->ctmp_2nodenum;
   int *tmp_hubs = spp->tmp->itmp_8nodenum + 4 * nodenum;
   int *tmp_hub_coef = spp->tmp->itmp_8nodenum + 5 * nodenum;
   int i, j, k, start, hub, max_lhs, cnt, max_hub, tmp;
   double lhs_loh, max_val;

   lhs_loh = lhs_oh;
   /* pick out all the nodes that are adjacent to at least one node on the
      odd hole (these will be the hub candidates).
      add up rows of node-node corresponding to the nodes in oh, this
      will tell how many adjacent oh nodes each node in fgraph has. */
   for (k = 0; k < nodenum; k++)
      num_nbrs[k] = 0;
   for (i = 0; i < oh_len; i++) {
      start = oh[i] * nodenum;
      for (k = 0; k < nodenum; k++)
	 num_nbrs[k] += (int) node_node[start + k];
   }
   for (i = 0; i < oh_len; i++)
      num_nbrs[oh[i]] = 0;      /* oh nodes can't be hubs */
   
   /* hub candidates are those with >= 1 num_nbrs value */
   for (k = 0, hub_len = 0; k < nodenum; k++)
      if (num_nbrs[k])
	 hubs[hub_len++] = k;
   if (hub_len == 0)
      return(lhs_loh);
   /* order the hubs randomly, this will make sure that ties are broken
      more or less randomly when comparing which hubs improves the most */
   for (i = hub_len-1; i > 0; i--) {
      j = (int) (floor((double)RANDOM()/MAXINT * (i+1)));
      tmp = hubs[i];
      hubs[i] = hubs[j];
      hubs[j] = tmp;
   }
   
   for (i = 0; i < spp->par->max_hub_num && i < hub_len; i++) {
      /* compute the lifting coefficient for each hub candidate.
         the first i-1 hubs are assumed to be already lifted */
      for (j = i; j < hub_len; j++) {
	 hub = hubs[j];
	 /* tmp_hubs and tmp_hub_coef will contain the indices and coefs
	    of hubs (from 0 to i-1) not adjacent to the hub currently
	    being lifted */
	 start = hub * nodenum;
	 for (k = 0, cnt = 0; k < i; k++)
	    if (!node_node[start + hubs[k]]) {
	       tmp_hubs[cnt] = hubs[k];
	       tmp_hub_coef[cnt++] = hub_coef[k];
	    }
	 /* compute max of lhs of the lifted oh assuming that hub is chosen */
	 for (k = 0; k < cnt; k++)
	    label[k] = FALSE;
	 max_lhs =
	    max_lhs_of_lifted_odd_hole(spp, oh_len, oh, hub, cnt, tmp_hubs,
				       tmp_hub_coef, label, 0);
	 hub_coef[j] = rhs - max_lhs;
      }
      /* compute which hub candidate increases the lhs the most */
      for (j = i, max_hub = -1, max_val = 0; j < hub_len; j++) {
	 if (hub_coef[j] * nodes[hubs[j]].val > max_val) {
	    max_hub = j;
	    max_val = hub_coef[j] * nodes[hubs[j]].val;
	 }
      }
      /* if max_val is 0 (all the hubs have coef 0), break out of loop */
      if (max_val == 0)
	 break;
      /* swap the best hub with the ith (also set hub_coef) */
      tmp = hubs[i];
      hubs[i] = hubs[max_hub];
      hubs[max_hub] = tmp;
      hub_coef[i] = hub_coef[max_hub];

      lhs_loh += max_val; 
   }
   *phub_len = i;
   return(lhs_loh);
}

#if 0
/*===========================================================================*/

/* phub_len, hubs and hub_coef are OUT, *pcost_oh contains the cost of the
   oh as an input and the cost of the lifted oh as an output.
   cost of oh (lifted oh) is the value of the lhs in the current soln */
/* if lifted oh is not violated *pcost_oh is unchanged, and the OUT
   arguments contain junk */

double lift_nonviolated_odd_hole(spp_cg_problem *spp, int oh_len, int *oh,
				 double lhs_oh, int *phub_len, int *hubs,
				 int *hub_coef, double etol)
{
   int nodenum = spp->fgraph->nodenum;
   fnode *nodes = spp->fgraph->nodes;
   char *node_node = spp->fgraph->node_node;
   int rhs = (oh_len - 1)/2;
   int hub_len = 0;
   int *num_nbrs = spp->tmp->itmp_8nodenum + 4 * nodenum;
   char *label = spp->tmp->ctmp_2nodenum;
   int *tmp_hubs = spp->tmp->itmp_8nodenum + 4 * nodenum;
   int *tmp_hub_coef = spp->tmp->itmp_8nodenum + 5 * nodenum;
   int i, j, k, start, hub, max_lhs, cnt;
   double lhs_loh;

   /* choose a set of at most max_hub_num hub candidates (each must be
      adjacent to at least one node in the oh, so we add up rows of
      node-node corresponding to the nodes in oh to see how many adjacent
      oh nodes each node in fgraph has) */
   for (k = 0; k < nodenum; k++)
      num_nbrs[k] = 0;
   for (i = 0; i < oh_len; i++) {
      start = oh[i] * nodenum;
      for (k = 0; k < nodenum; k++)
	 num_nbrs[k] += (int) node_node[start + k];
   }
   for (i = 0; i < oh_len; i++)
      num_nbrs[oh[i]] = 0;      /* oh nodes can't be hubs */
   
   /* hub candidates are those with >= 1 num_nbrs value, so order all the nodes
      in decr order of their num_nbrs values */
   for (k = 0; k < nodenum; k++)
      hubs[k] = k;
   qsort_ii(num_nbrs, hubs, nodenum);
   spp_reverse_int_string(nodenum, num_nbrs); /* qsort orders into incr */
   spp_reverse_int_string(nodenum, hubs);
   for (k = 0; k < nodenum && num_nbrs[k]; k++);  /* k is pos of first 0 */
   hub_len = MIN(spp->par->max_hub_num, k);

   /* alternative way of ordering the hubs: into decreasing order of their
      x values */
   /*
   for (k = 0; k < nodenum; k++) {
      hubs[k] = k;
      if (num_nbrs[k]) {
	 dtmp[k] = nodes[k].val;
      } else {
	 dtmp[k] = -1;
      }
   }
   qsort_di(dtmp, hubs, nodenum);
   spp_reverse_double_string(nodenum, dtmp);
   spp_reverse_int_string(nodenum, hubs);
   for (k = 0; k < nodenum && dtmp[k] >= 0; k++);
   hub_len = MIN(spp->par->max_hub_num, k);
   */

   /* lift the hubs one by one */
   for (i = 0; i < hub_len; i++) {

      hub = hubs[i];
      /* tmp_hubs and tmp_hub_coef will contain the indices and coefs of
	 hubs not adjacent to the hub currently being lifted            */
      start = hub * nodenum;
      for (j = 0, cnt = 0; j < i; j++)
	 if (!node_node[start + hubs[j]]) {
	    tmp_hubs[cnt] = hubs[j];
	    tmp_hub_coef[cnt++] = hub_coef[j];
	 }
      /* compute max of lhs of the lifted oh assuming that hub is chosen */
      for (j = 0; j < cnt; j++)
	 label[j] = FALSE;
      max_lhs =
	 max_lhs_of_lifted_odd_hole(spp, oh_len, oh, hub, cnt, tmp_hubs,
				    tmp_hub_coef, label, 0);
      if (max_lhs == rhs) {
	 /* coef would be 0, delete this hub from the list */
	 for (j = i+1; j < hub_len; j++)
	    hubs[j-1] = hubs[j];
	 hub_len--;
	 i--;
	 continue;
      } else {
	 hub_coef[i] = rhs - max_lhs;
      }

      /* evaluate lhs and return if lifted oh is violated by the
	 current solution (do this only if parameter is set)             */
      if (spp->par->eval_oh_during_lifting) {
	 lhs_loh = lhs_oh;
	 for (j = 0; j <= i; j++)
	    lhs_loh += hub_coef[j] * nodes[hubs[j]].val;
	 if (lhs_loh > rhs + etol) {
	    *phub_len = i+1;
	    return(lhs_loh);
	 }
      }
   }

   /* evaluate lhs */
   lhs_loh = lhs_oh;
   for (j = 0; j < hub_len; j++)
      lhs_loh += hub_coef[j] * nodes[hubs[j]].val;
   if (lhs_loh > rhs + spp->soln->lpetol) {
      *phub_len = hub_len;
      return(lhs_loh);
   } 
   return(lhs_oh);
}
#endif

/*===========================================================================*/

/* returns the max value of the lhs of the lifted odd hole provided that
   the hubs labeled by TRUE are set to 1.
   oh and hubs contain indices wrt fgraph
   label (T/F) indicates which hubs are at value 1 in the current solution
   pos position within hubs (and label), hubs up to position pos are
   permanently labeled.
   hub is the hub to be lifted, needs to be passed on since its neighbors
   on the odd hole need to be marked as well */

int max_lhs_of_lifted_odd_hole(spp_cg_problem *spp, int oh_len, int *oh,
			       int hub, int hub_len, int *hubs, int *hub_coef,
			       char *label, int pos)
{
   int nodenum = spp->fgraph->nodenum;
   fnode *nodes = spp->fgraph->nodes;
   char *node_node = spp->fgraph->node_node;
   int i, j, k, start, max_lhs, ret, *nbrs;
   int *oh_clone = spp->tmp->itmp_8nodenum + 6 * nodenum;
   int *perm = spp->tmp->itmp_8nodenum + 7 * nodenum;
   char *oh_label = spp->tmp->ctmp_2nodenum + nodenum;

   /* pos will contain the position of the first hub that is nonadjacent to
      all hubs already labeled TRUE */
   for ( ; pos < hub_len; pos++) {
      start = hubs[pos] * nodenum;
      for (j = 0; j < pos; j++)
	 if (label[j] && node_node[start + hubs[j]])
	    break; /* neighbor to an earlier... */
      if (j == pos)
	 break; /* no neighbor from 0 to pos-1 */
      label[pos] = FALSE;
   }

   /* max_lhs is the largest possible lhs value provided that the hubs
      up to position pos are permanently labeled */
   max_lhs = 0;

   /* if not all nodes are labeled, recurse by setting the last node labeled
      TRUE once to TRUE and once to FALSE; ow compute the maximal lhs value */
   if (pos < hub_len) {
      label[pos] = TRUE;
      ret = max_lhs_of_lifted_odd_hole(spp, oh_len, oh, hub, hub_len, hubs,
				       hub_coef, label, pos+1);
      max_lhs = MAX(max_lhs, ret);
      label[pos] = FALSE;
      ret = max_lhs_of_lifted_odd_hole(spp, oh_len, oh, hub, hub_len, hubs,
				       hub_coef, label, pos+1);
      max_lhs = MAX(max_lhs, ret);

   } else {
      /* we introduce a labeling (oh_label) on oh that indicates which nodes
	 are not neighbors to any of the hubs currently set to 1.
	 first order the nodes in oh into increasing order of their indices
	 so that scanning thru the neighbors of hubs will be easy.
	 perm is an array that will contain the permutation (will need
	 to permute back oh and oh_label) */
      memcpy(oh_clone, oh, oh_len * ISIZE);
      for (i = 0; i < oh_len; i++) {
	 oh_label[i] = TRUE;
	 perm[i] = i;
      }
      qsort_ii(oh_clone, perm, oh_len);
      for (j = 0; j < hub_len; j++)
	 if (label[j]) {
	    /* need to set oh_label to FALSE for every index common in oh
	       and the adjacency list of the jth hub */
	    nbrs = nodes[hubs[j]].nbrs;
	    for (i = oh_len-1, k = nodes[hubs[j]].degree-1; i >= 0 && k >= 0; )
	       if (oh_clone[i] == nbrs[k]) {
		  oh_label[i] = FALSE;
		  i--; k--;
	       } else if (oh_clone[i] < nbrs[k]) {
		  k--;
	       } else {
		  i--;
	       }
	 }
      /* do the same for hub */
      nbrs = nodes[hub].nbrs;
      for (i = oh_len-1, k = nodes[hub].degree-1; i >= 0 && k >= 0; )
	 if (oh_clone[i] == nbrs[k]) {
	    oh_label[i] = FALSE;
	    i--; k--;
	 } else if (oh_clone[i] < nbrs[k]) {
	    k--;
	 } else {
	    i--;
	 }
      /* permute back oh_label */
      qsort_ic(perm, oh_label, oh_len);

      /* now compute the max value of the lhs: coeffs of hubs at 1 +
	 ceil(|S|/2) for each segment of the oh (segments: cont sequence
	 of nodes that are not neigbors of any of the hubs at 1 (nodes
	 marked TRUE in oh_label) */
      for (j = 0; j < hub_len; j++)
	 if (label[j])
	    max_lhs += hub_coef[j];
      /* find first false (there must be at least one since all hubs are
	 adjacent to some nodes in oh) */
      for (i = 0; i < oh_len && oh_label[i]; i++);
      ret = i;   /* save position of first FALSE */
      while (i < oh_len) {
	 /* find next FALSE */
	 for (k = i + 1; k < oh_len && oh_label[k]; k++);
	 if (k == oh_len) {
	    /* last segment is between last and first FALSE */
	    max_lhs += (ret + k - i) >> 1;
	    break;
	 }
	 max_lhs += (k - i) >> 1;
	 i = k;
      }
   }
   return(max_lhs);
}


/*****************************************************************************/
/*****************************************************************************/
/*              ODD ANTIHOLES                                                */
/*****************************************************************************/
/*****************************************************************************/

int find_violated_odd_antiholes(spp_cg_problem *spp, double etol)
{
   int nodenum = spp->cfgraph->nodenum;
   fnode *nodes = spp->cfgraph->nodes;
   char *node_node = spp->cfgraph->node_node;
   int *lnodes = spp->lgraph->lnodes;
   int *lbeg = spp->lgraph->lbeg;
   int *roots = spp->tmp->itmp_8nodenum;
   int *oah = spp->tmp->itmp_8nodenum + nodenum;
   int *hubs = spp->tmp->itmp_8nodenum + 2 * nodenum;
   int *hub_coef = spp->tmp->itmp_8nodenum + 3 * nodenum;
   int *itmp = spp->tmp->itmp_8nodenum + 7 * nodenum;
   double *dtmp = spp->tmp->dtmp_2nodenum;
   cut_data *new_cut = spp->tmp->cuttmp;
   int begl, endl, levelnum, *coef;
   int cnt, num_roots, random_num, tmp, oah_len, hub_len, numcuts = 0;
   int i, j, l, u, v, w;
   double lhs_oah, violation, *dcoef;

   /* collect the non-isolated nodes of cfgraph into roots */
   for (i = 0, num_roots = 0; i < nodenum; i++) {
      if (nodes[i].degree)
	 roots[num_roots++] = i;
   }
   if (num_roots == 0)
      return(numcuts);    /* all nodes isolated */
   /* order roots randomly: swap ith with one randomly chosen bw 0 and i */
   for (i = num_roots-1; i > 0; i--) {
      random_num = (int) (floor((double)RANDOM()/MAXINT * (i+1)));
      tmp = roots[i];
      roots[i] = roots[random_num];
      roots[random_num] = tmp;
   }
   /* we will process only 20 to 50 percent of the possible roots, depending
      on the density of the graph. make this a parameter!                   */
   num_roots = (int) (ceil((double)(.2 + .3 * spp->cfgraph->density)*num_roots));

   for (i = 0; i < num_roots; i++) {
      v = roots[i];
      /* construct level graph with root v and display it */
      construct_level_graph(spp->cfgraph, v, spp->lgraph);
      /* display_level_graph(spp, spp->cfgraph); */
      
      /* for each level >= 2 */
      levelnum = spp->lgraph->levelnum;
      for (l = 2; l < levelnum; l++) {
	 begl = lbeg[l]; endl = lbeg[l+1];
	 /* if there is at most one node on this level: continue */
	 if (endl - begl <= 1)
	    continue;
	 oah_len = 2 * l + 1;

	 /* examine each pair of adjacent nodes on this level.
	    note: u and w are indices wrt lgraph here, so lnodes[u] and
	    lnodes[w] are the indices wrt fgraph!                       */
	 for (u = begl; u < endl - 1; u++) { 
	    for (w = u + 1; w < endl; w++) {
	       /* if the nodes are adjacent try to find paths from u and w
		  to the root (v) */
	       if (node_node[lnodes[u] * nodenum + lnodes[w]]) {
		  lhs_oah = find_chordless_oh(spp, spp->cfgraph,
					      lnodes[u], lnodes[w],oah);
		  if (lhs_oah > -1) {
		     /* display_level_graph(spp, spp->cfgraph); */
		     if (lhs_oah > 2 + etol) {
			/* odd antihole is violated: send back cut */
			coef = (int *)(dtmp);
			for (j = 0; j < oah_len; j++)
			   coef[j] = nodes[oah[j]].ind;
			rotate_odd_hole(oah_len, coef, itmp);
			memcpy(new_cut->coef, coef, oah_len * ISIZE);
			new_cut->type = ODD_ANTIHOLE;
			new_cut->size = oah_len * ISIZE;
			new_cut->rhs = 2;
			new_cut->range = 0;
			new_cut->sense = 'L';
			violation = lhs_oah - 2;
			numcuts +=
			   register_and_send_cut(spp, new_cut, violation, etol);
		     } else {
			/* odd antihole is not violated: try to lift */
			/* display_level_graph(spp, spp->cfgraph); */
			lhs_oah =
			   lift_nonviolated_odd_antihole(spp, oah_len, oah,
							 lhs_oah, &hub_len,
							 hubs, hub_coef, etol);
			if (lhs_oah > 2 + etol) {
			   /* lifted odd antihole is violated: send back cut */
			   coef = (int *)(dtmp);
			   coef[0] = oah_len;
			   coef[1] = hub_len;
			   for (j = 0, cnt = 2; j < oah_len; j++)
			      coef[cnt++] = nodes[oah[j]].ind;
			   rotate_odd_hole(oah_len, coef + 2, itmp);
			   for (j = 0; j < hub_len; j++)
			      coef[cnt++] = nodes[hubs[j]].ind;
			   memcpy(new_cut->coef, coef, cnt * ISIZE);
			   dcoef = dtmp;
			   for (j = 0; j < hub_len; j++)
			      dcoef[j] = (double) hub_coef[j];
			   memcpy(new_cut->coef + cnt * ISIZE, dcoef,
				  hub_len * DSIZE);
			   new_cut->type = ODD_ANTIHOLE_LIFTED;
			   new_cut->size = cnt * ISIZE + hub_len * DSIZE;
			   new_cut->rhs = 2;
			   new_cut->range = 0;
			   new_cut->sense = 'L';
			   violation = lhs_oah - l;
			   numcuts +=
			      register_and_send_cut(spp, new_cut, violation,etol);
			}
			/* undisplay_level_graph(spp); */
		     }
		     /* undisplay_level_graph(spp); */
		  }
	       } /* endif u, w adjacent */
	    } /* endfor w */
	 } /* endfor u */
      } /* endfor l */
      /* undisplay_level_graph(spp); */
   } /* endfor i */
   return(numcuts);
}

/*===========================================================================*/

double lift_nonviolated_odd_antihole(spp_cg_problem *spp, int oah_len,
				     int *oah, double lhs_oah, int *phub_len,
				     int *hubs, int *hub_coef, double etol)
{
   int nodenum = spp->fgraph->nodenum;
   fnode *nodes = spp->fgraph->nodes;
   char *node_node = spp->fgraph->node_node;
   int hub_len = 0;
   int *num_nbrs = spp->tmp->itmp_8nodenum + 4 * nodenum;
   int *tmp_nbrs = spp->tmp->itmp_8nodenum + 4 * nodenum;
   int i, j, k, l, tmp, max_hub, start, hub, cnt;
   double lhs_loah, max_val;

   lhs_loah = lhs_oah;
   /* pick out all the nodes that are adjacent to at least one node on the
      odd antihole (these will be the hub candidates).
      add up rows of node-node corresponding to the nodes in oah, this
      will tell how many adjacent oah nodes each node in fgraph has. */
   for (k = 0; k < nodenum; k++)
      num_nbrs[k] = 0;
   for (i = 0; i < oah_len; i++) {
      start = oah[i] * nodenum;
      for (k = 0; k < nodenum; k++)
	 num_nbrs[k] += (int) node_node[start + k];
   }
   for (i = 0; i < oah_len; i++)
      num_nbrs[oah[i]] = 0;      /* oah nodes can't be hubs */
   
   /* hub candidates are those with >= (oah_len+1)/2 num_nbrs value */
   tmp = (oah_len + 1) / 2;
   for (k = 0, hub_len = 0; k < nodenum; k++)
      if (num_nbrs[k] >= tmp)
	 hubs[hub_len++] = k;
   if (hub_len == 0)
      return(lhs_loah);
   /* order the hubs randomly, this will make sure that ties are broken
      more or less randomly when comparing which hubs improves the most */
   for (i = hub_len-1; i > 0; i--) {
      j = (int) (floor((double)RANDOM()/MAXINT * (i+1)));
      tmp = hubs[i];
      hubs[i] = hubs[j];
      hubs[j] = tmp;
   }

   for (i = 0; i < spp->par->max_hub_num && i < hub_len; i++) {
      /* compute the lifting coefficient for each hub candidate, the first
	 i-1 hubs are assumed to be already lifted. */
      for (j = i; j < hub_len; j++) {
	 hub = hubs[j];
	 /* tmp_nbrs will contain the indices of oah nodes and already lifted
	    hubs (from 0 to i-1) not adjacent to hub */
	 start = hub * nodenum;
	 for (k = 0, cnt = 0; k < oah_len; k++)
	    if (!node_node[start + oah[k]])
	       tmp_nbrs[cnt++] = oah[k];
	 for (k = 0; k < i; k++)
	    if (!node_node[start + hubs[k]])
	       tmp_nbrs[cnt++] = hubs[k];
	 /* if there are no such indices: the coeff of the currently lifted
	    hub is 2 (since the max of the lhs is 0) */
	 if (cnt == 0) {
	    hub_coef[j] = 2;
	    continue;
	 }
	 /* hub cannot be adjacent to an already lifted hub with coeff 2 */
	 /* if any two nodes in the list are not adjacent, they can be
	    both chosen, so hub's coeff is 0; ow hub's coeff is 1 */
	 hub_coef[j] = 1;
	 for (k = cnt - 1; k >= 1; k--) {
	    start = tmp_nbrs[k] * nodenum;
	    for (l = k - 1; l >= 0; l--)
	       if (!node_node[start + tmp_nbrs[l]]) {
		  hub_coef[j] = 0;
		  break;
	       }
	    if (l >= 0)
	       break;
	 }
      } /* endfor j */

      /* compute which hub candidate increases the lhs the most */
      for (j = i, max_hub = -1, max_val = 0; j < hub_len; j++) {
	 if (hub_coef[j] * nodes[hubs[j]].val > max_val) {
	    max_hub = j;
	    max_val = hub_coef[j] * nodes[hubs[j]].val;
	 }
      }
      /* if max_val is 0 (all the hubs have coef 0), break out of loop */
      if (max_val == 0)
	 break;
      /* swap the best hub with the ith */
      tmp = hubs[i];
      hubs[i] = hubs[max_hub];
      hubs[max_hub] = tmp;
      tmp = hub_coef[i];
      hub_coef[i] = hub_coef[max_hub];
      hub_coef[max_hub] = tmp;

      lhs_loah += max_val;

      /* if coef of chosen hub is 2, set the coefs of its neighbors to 0 */
      if (hub_coef[i] == 2) {
	 start = hubs[i] * nodenum;
	 for (j = i+1; j < hub_len; j++)
	    if (node_node[start + hubs[j]])
	       hub_coef[j] = 0;
      }
      /* hub candidates with hub_coef 0 will never have a positive coef,
	 so shuffle them into the end of the sequence and decrease hub_len
	 accordingly (k is where the next non0 can be written) */
      for (j = k = i+1; j < hub_len; j++)
	 if (hub_coef[j] != 0)
	    hubs[k++] = hubs[j];
      hub_len = k;
   } /* endfor i */
   *phub_len = i;
   return(lhs_loah);
}

