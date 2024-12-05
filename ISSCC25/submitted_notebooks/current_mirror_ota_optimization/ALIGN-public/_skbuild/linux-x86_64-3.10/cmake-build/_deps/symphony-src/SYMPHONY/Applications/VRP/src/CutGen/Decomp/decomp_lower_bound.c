#include <math.h>
#include <memory.h>
#include <stdlib.h>

#include "BB_constants.h"
#include "BB_macros.h"
#include "decomp.h"
#include "my_decomp.h"
#include "vrp_macros.h"
#include "vrp_sym_cg.h"
#include "vrp_const.h"
#include "vrp_common_types.h"
#include "sym_proccomm.h"
#include "compute_cost.h"
#include "decomp_lower_bound.h"
#include "vrp_sym_dg.h"
#ifdef EXACT_LIFTING
#include "util.h"
#include "tinytsp.h"
#endif

typedef struct DBL_NEIGHBOR{ /* a neighbor to a set of nodes */
   int nbor;    /* the index of the neighbor */
   int host;    /* the node in the set st. host-nbor edge is the cheapest */
   double cost;    /* the cost of that cheapest edge */
}dbl_neighbor;

/*===========================================================================*/

#ifdef EXACT_LIFTING

double decomp_lower_bound(cg_vrp_spec *vrp, double *edge_costs, int *x,
			  int adjust, int mult)
{
   int edgenum = (vrp->vertnum)*(vrp->vertnum-1)/2;
   int *upper = (int *) calloc(edgenum, ISIZE);
   int *lower = (int *) calloc(edgenum, ISIZE);
   int i, j, k, rval;
   double ub = (double)((MAXINT)/(vrp->vertnum+vrp->numroutes-1)), optval = 0;
   
#ifndef NO_LIFTING
   double *costs = (double *) calloc(edgenum, DSIZE);

   /*FIXME: Here, we should check whether the upper bound on the depot edges
     really are 2.0 or whether they can be taken to be 1.0 */
   for (i = 1, k = 0; i < vrp->vertnum; i++){
      for (j = 0; j < i; j++){
	 if (edge_costs[k] == ub){
	    k++;
	 }else if (edge_costs[k] == -100000){
	    lower[k] = 1.0;
	    upper[k++] = (j == 0 ? 2.0 : 1.0);
	 }else{
	    upper[k] = (j == 0 ? 2.0 : 1.0);
	    costs[k] = edge_costs[k++];
	 }
      }
   }
   
   rval = CCtiny_bnc_msp(vrp->vertnum, edgenum, vrp->edges, costs, 0, lower,
			 upper, &ub, CC_TINYTSP_MINIMIZE, &optval, x, 0, 100,
			 vrp->numroutes);
   FREE(upper);
   FREE(lower);
   FREE(costs);
#else
#ifdef COMPILE_IN_CG
   lp_prob *lp = get_lp_ptr(NULL);
   LPdata *lp_data2 = lp->lp_data;

   for (i = 0, k = 0; i < edgenum; i++){
      if (k >= lp_data2->n || lp_data2->vars[k]->userind > i){
	 /*Not in the problem -- upper[i] = lower[i] = 0.0*/
      }else{
	 upper[i] = lp_data2->ub[k];
	 lower[i] = lp_data2->lb[k++];
      }
   }
   
#else
   
   for (i = 1, k = 0; i < vrp->vertnum; i++){
      for (j = 0; j < i; j++){
	 upper[k++] = (j == 0 ? 2.0 : 1.0);
      }
   }

#endif
   
   rval = CCtiny_bnc_msp(vrp->vertnum, edgenum, vrp->edges, edge_costs, 0,
			 lower, upper, &ub, CC_TINYTSP_MINIMIZE,
			 &optval, x, 0, 100, vrp->numroutes);
   FREE(upper);
   FREE(lower);
#endif
   
   return(rval ? MAXDOUBLE : optval);
}

/*===========================================================================*/

#else

static int edgecompar(const void *edge1, const void *edge2)
{
   return(((dbl_edge_data *)edge1)->cost-((dbl_edge_data *)edge2)->cost ?
	  (((dbl_edge_data *)edge1)->cost-((dbl_edge_data *)edge2)->cost)/
	  fabs(((dbl_edge_data *)edge1)->cost-((dbl_edge_data *)edge2)->cost):
	  0);
}

/*===========================================================================*/

double decomp_lower_bound(cg_vrp_spec *vrp, double *edge_costs, int *x,
			  int adjust, int mult)
{
  int *tree;
  double bound, tree_cost;
  int cur_node, vertnum = vrp->vertnum, numroutes = vrp->numroutes, i;
  dbl_edge_data *depot_costs;


  /*-------------------------------------------------------------------*\
  | Calculate a k-degree-centre-tree with penalties lamda               |
  \*-------------------------------------------------------------------*/
    
  tree = (int *) calloc(vertnum, sizeof(int));
  depot_costs    = (dbl_edge_data *) calloc(vertnum-1, sizeof(dbl_edge_data));

  tree_cost = decomp_make_k_tree(vrp, edge_costs, tree, numroutes);

  /*-------------------------------------------------------------------*\
  | Construct a sorted list of the cheapest edges adjacent to the depot |
  \*-------------------------------------------------------------------*/

  for (cur_node = 1; cur_node < vertnum; cur_node++){
     depot_costs[cur_node-1].cost =
	((edge_costs[INDEX(0, cur_node)] == -100000) ?
	 0 : edge_costs[INDEX(0, cur_node)]);
     depot_costs[cur_node-1].v1 = cur_node;
  }
	
  qsort(depot_costs, vertnum-1, sizeof(dbl_edge_data), edgecompar);
  
  for (bound = i = 0; i < numroutes; i++)
     bound += depot_costs[i].cost; /* == -100000) ? 0 : depot_costs[i].cost;*/
  
  bound += tree_cost;
  
  FREE(tree);
  FREE(depot_costs);
  
  return(bound + 100000.0 * ((double)adjust));
}

/*--------------------------------------------------------------------------*\
| This routine creates a minimum k-degree-centre-tree based on the     |
| penalized costs. It first dreates a regular spanning tree and then either  |
| forces edges adjacent to the depot either in or out in order to make the   |
| degree of the depot correct. Edges are forced in and out by subtracting or |
| adding a constant to all the depot edge costs and forming a new minimum    |
| spanning tree.                                                             |
\*--------------------------------------------------------------------------*/
	
double decomp_make_k_tree(cg_vrp_spec *vrp, double *edge_costs, int *tree,
			  int k)
{
  int nearnode, size;
  int host, vertnum = vrp->vertnum, break_node = 0, new_depot_node = 0, i;
  int depot_degree = 0, cur_node, prev_node, next_node, max_node = 0;
  int mu = 0, next_mu, last = 0;
  double cost = 0, max_cost;
  int *intree = NULL;
  dbl_neighbor *nbtree = NULL;

  while (TRUE){
    intree = (int *) calloc (vertnum, sizeof(int));
    nbtree = (dbl_neighbor *) calloc (vertnum, sizeof(dbl_neighbor));
    cost = 0;
    last = 0;
    intree[0] = IN_TREE;
    decomp_insert_edges(vrp, edge_costs, 0, nbtree, intree, &last, mu);

    /*-----------------------------------------------------------------------*\
    | Calculate the minimum spanning tree by adding in the nearest node to the|
    | current tree as long as it does not form a cycle.                       |
    \*-----------------------------------------------------------------------*/
    
    for (size = 1; size < vertnum ; size++){
      nearnode = decomp_closest(nbtree, intree, &last, &host);
      intree[nearnode] = IN_TREE;
      tree[nearnode] = host;
      cost += edge_costs[INDEX(host, nearnode)];
      decomp_insert_edges(vrp, edge_costs, nearnode, nbtree, intree, &last, 
			  mu);
    }

    /*----------------------------------------------------------------------*\
    | Calculate the degree of the depot in the current tree                  |
    \*----------------------------------------------------------------------*/

    for (depot_degree = 0, cur_node = 1; cur_node < vertnum; cur_node++){
      if (!tree[cur_node])
	depot_degree++;
    }

    /*-----------------------------------------------------------------------*\
    | If the degree of the depot is as desired, then we are done. If it is too|
    | small, then we can easily determine the next edge to add adjacent to the|
    | depot in order to increase the degree of the depot. We add the edge that|
    | increase the cost of the tree the least by determining which other edge |
    | in the tree would be forced out. In this case, we don't need to         |
    | recompute the tree from scratch. We simply make the appropriate switch. |
    | If the degree is too large, we cannot                                   |
    | compute the leaving edge so easily. Then we simply raise the cost of all|
    | edges asjacent to the depot by an amount sufficient to force enough     |
    | edges out of the solution. In this case, we do have to recompute the    |
    | tree                                                                    |
    \*-----------------------------------------------------------------------*/

    if (depot_degree == k) break;

    if (depot_degree < k){
      while (depot_degree < k){
	next_mu = MAXINT;
	for (i = 1; i<vertnum; i++)
	  if (tree[i]){
	    max_cost = -MAXINT;
	    for (cur_node = i; tree[cur_node]; cur_node = tree[cur_node])
	      if ((cost = edge_costs[INDEX(tree[cur_node], cur_node)]) >
		  max_cost){
		max_cost = cost;
		max_node = cur_node;
	      }
	    if ((cost = edge_costs[INDEX(0, i)] - max_cost) < next_mu){
	      next_mu = cost;
	      new_depot_node = i;
	      break_node = max_node;
	    }
	  }
	for (prev_node = new_depot_node, cur_node = tree[new_depot_node],
	     next_node = tree[cur_node]; prev_node != break_node;
	     tree[cur_node] = prev_node, prev_node = cur_node,
	     cur_node = next_node, next_node = tree[next_node]);
	
	tree[new_depot_node] = 0;
	
	for (depot_degree = 0, cur_node = 1; cur_node < vertnum; cur_node++)
	  if (!tree[cur_node])
	    depot_degree++;

      }
      for (cost = 0, cur_node = 1; cur_node < vertnum; cur_node++)
	cost += edge_costs[INDEX(cur_node, tree[cur_node])];
      
      break;
    }
    else{ /*depot_degree > k*/

      mu -= MAX(edge_costs[INDEX(0, 1)], 1);
      
      if (intree) free((char *) intree);
      if (nbtree) free((char *) nbtree);
    }
  }

  free ((char *)intree);
  free ((char *)nbtree);
  return(cost);
}

/*===========================================================================*/

int decomp_closest(dbl_neighbor *nbtree, int *intree, int *last, int *host)
{
  int closest_node;
  int pos, ch;
  double cost;
  dbl_neighbor temp;

  /*-----------------------------------------------------------------------*\
  | This routine deletes the item from the top of the binary tree where the |
  | distances are stored and adjusts the tree accordingly                   |
  \*-----------------------------------------------------------------------*/
  
  closest_node = nbtree[1].nbor;
  *host = nbtree[1].host;
  (void) memcpy ((char *)&temp, (char *)(nbtree+*last), sizeof(dbl_neighbor));
  cost = nbtree[*last].cost;
  --*last;
  pos = 1;
  while ((ch=2*pos) < *last){
    if ((nbtree[ch].cost > nbtree[ch+1].cost)||
	((nbtree[ch].cost == nbtree[ch+1].cost) && !nbtree[ch+1].host))
      ch++;
    if (cost <= nbtree[ch].cost)
      break;
    intree[nbtree[ch].nbor] = pos;
    (void) memcpy ((char *)(nbtree+pos), 
		   (char *)(nbtree+ch), sizeof(dbl_neighbor));
    pos = ch;
  }
  if (ch == *last){
    if (cost > nbtree[ch].cost){
      intree[nbtree[ch].nbor] = pos;
      (void) memcpy ((char *)(nbtree+pos), 
		     (char *)(nbtree+ch), sizeof(dbl_neighbor));
      pos=ch;
    }
  }
  intree[temp.nbor] = pos;
  (void) memcpy ((char *)(nbtree+pos), (char *)&temp, sizeof(dbl_neighbor));
  return(closest_node);
}

/*===========================================================================*/

void decomp_insert_edges(cg_vrp_spec *vrp, double *edge_costs, int new_node,
			 dbl_neighbor *nbtree, int *intree, int *last, int mu)
/*--------------------------------------------------------------------------*\
|  Scan through the edges incident to 'new_node' - the new node in the set.  |
|  If the other end 'i' is in the set, do nothing.                           |
|  If the other end is not in nbtree then insert it.                         |
|  Otherwise update its distance if necessary:                               |
|     If the previous closest point of the set to 'i' is closer then         |
|     'new_node' then we don't have to do anything, otherwise update.        |
|     (update: the min element is on the top of the tree                     |
|              Therefore the insertion and the update parts can be done      |
|              with the same code, not like in fi_insert_edges.)             |
\*--------------------------------------------------------------------------*/
{
  double cost = 0, prevcost;
  int pos = 0, ch;
  int i;
  int vertnum = vrp->vertnum;
  
  for (i=0; i<vertnum; i++){
    if (intree[i] != IN_TREE){
      cost = edge_costs[INDEX(new_node, i)] - (i ? 0:mu) - (new_node ? 0:mu);
      if (intree[i] == NOT_NEIGHBOR){
	pos = ++(*last);
	prevcost = cost+1;
      }else{
	prevcost = nbtree[pos = intree[i]].cost;
      }
      if (prevcost > cost){
	while ((ch=pos/2) != 0){
	  if ((nbtree[ch].cost < cost)||
	      ((nbtree[ch].cost == cost) && !nbtree[ch].host))
	    break;
	  intree[nbtree[ch].nbor] = pos;
	  (void) memcpy ((char *)(nbtree+pos), 
			 (char *)(nbtree+ch), sizeof(dbl_neighbor));
	  pos = ch;
	}
	nbtree[pos].nbor = i;
	nbtree[pos].host = new_node;
	nbtree[pos].cost = cost;
	intree[i] = pos;
      }
    }
  }
}

/*--------------------------------------------------------------------------*\
| This routine computes the new penaltie for use in computing the lower bound|
| The penalties are based on the amount of violation of the degree           |
| constraints in the current lower bound.                                    |
\*--------------------------------------------------------------------------*/
    
int decomp_new_lamda(cg_vrp_spec *vrp, int upper_bound, int cur_bound,
		     int *lamda, int numroutes, int *tree,
		     dbl_edge_data *cur_edges, int alpha)
{
  int denom = 0;
  int cur_node1, cur_node2, vertnum = vrp->vertnum, i;
  int *degrees;

  degrees = (int *) calloc (vertnum, sizeof(int));
  
  for (cur_node1 = 0; cur_node1 < vertnum; cur_node1++){
    for (cur_node2 = 0; cur_node2 < vertnum; cur_node2++)
      if ((cur_node1 != cur_node2) && (tree[cur_node2] == cur_node1))
	degrees[cur_node1]++;
  }

  for (i = 0; i < numroutes; i++){
    degrees[cur_edges[i].v0]++;
    degrees[cur_edges[i].v1]++;
  }

  for (cur_node1 = 0; cur_node1 < vertnum; cur_node1++)
    denom += cur_node1 ? (degrees[cur_node1]-1)*(degrees[cur_node1]-1) :
      (degrees[cur_node1]-2*numroutes)*(degrees[cur_node1]-2*numroutes);
  
  denom = (int) sqrt((double)denom);

  if (!denom) return(1);

  for (cur_node1 = 0; cur_node1 < vertnum; cur_node1++)
    lamda[cur_node1] += (degrees[cur_node1] -
				    (cur_node1 ? 1: 2*numroutes));

  if (degrees) free((char *) degrees);
							   
  return(0);
}

#endif
