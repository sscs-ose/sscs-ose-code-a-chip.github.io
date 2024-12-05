/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/* This file was modified by Ali Pilatin January, 2005 (alp8@lehigh.edu)     */
/*                                                                           */
/* (c) Copyright 2000-2005 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include <math.h>
#include <stddef.h>

#include "sym_constants.h"
#include "mst_ins_rout.h"
#include "vrp_const.h"
#include "compute_cost.h"
#include <string.h>
/*--------------------------------------------------------------------------*\
| This first routine creates a minimum k-degree-centre-tree based on the     |
| penalized costs. It first dreates a regular spanning tree and then either  |
| forces edges adjacent to the depot either in or out in order to make the   |
| degree of the depot correct. Edges are forced in and out by subtracting or |
| adding a constant to all the depot edge costs and forming a new minimum    |
| spanning tree.                                                             |
\*--------------------------------------------------------------------------*/
	
int make_k_tree(lb_prob *p, int *tree, int *lamda, int k)
{
  int nearnode, size;
  int host, vertnum = p->vertnum, break_node = 0, new_depot_node = 0, i;
  int depot_degree = 0, cur_node, prev_node, next_node, max_node = 0;
  int mu = 0, next_mu, cost = 0, last = 0;
  int *intree = NULL, max_cost;
  neighbor *nbtree = NULL;

  while (TRUE){
    intree = (int *) calloc (vertnum, sizeof(int));
    nbtree = (neighbor *) calloc (vertnum, sizeof(neighbor ));
    cost = 0;
    last = 0;
    intree[0] = IN_TREE;
    ni_insert_edges(p, 0, nbtree, intree, &last, lamda, mu);

    /*-----------------------------------------------------------------------*\
    | Calculate the minimum spanning tree by adding in the nearest node to the|
    | current tree as long as it does not form a cycle.                       |
    \*-----------------------------------------------------------------------*/
    
    for (size = 1; size < vertnum ; size++){
      nearnode = closest(nbtree, intree, &last, &host);
      intree[nearnode] = IN_TREE;
      tree[nearnode] = host;
      cost += MCOST(&p->dist, host, nearnode, lamda);
      ni_insert_edges(p, nearnode, nbtree, intree, &last, lamda, mu);
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
	      if ((cost = MCOST(&p->dist, tree[cur_node], cur_node, lamda)) >
		  max_cost){
		max_cost = cost;
		max_node = cur_node;
	      }
	    if ((cost = MCOST(&p->dist, 0, i, lamda) - max_cost) < next_mu){
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
	cost += MCOST(&p->dist, cur_node, tree[cur_node], lamda);
      
      break;
    }
    else{ /*depot_degree > k*/

      mu -= ICOST(&p->dist, 0,1);
      
      if (intree) free((char *) intree);
      if (nbtree) free((char *) nbtree);
    }
  }

  free ((char *)intree);
  free ((char *)nbtree);
  return(cost);
}

/*===========================================================================*/

int closest(neighbor *nbtree, int *intree, int *last, int *host)
{
  int closest_node;
  int pos, ch;
  int cost;
  neighbor temp;

  /*-----------------------------------------------------------------------*\
  | This routine deletes the item from the top of the binary tree where the |
  | distances are stored and adjusts the tree accordingly                   |
  \*-----------------------------------------------------------------------*/
  
  closest_node = nbtree[1].nbor;
  *host = nbtree[1].host;
  (void) memcpy ((char *)&temp, (char *)(nbtree+*last), sizeof(neighbor));
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
		   (char *)(nbtree+ch), sizeof(neighbor));
    pos = ch;
  }
  if (ch == *last){
    if (cost > nbtree[ch].cost){
      intree[nbtree[ch].nbor] = pos;
      (void) memcpy ((char *)(nbtree+pos), 
		     (char *)(nbtree+ch), sizeof(neighbor));
      pos=ch;
    }
  }
  intree[temp.nbor] = pos;
  (void) memcpy ((char *)(nbtree+pos), (char *)&temp, sizeof(neighbor));
  return(closest_node);
}

/*===========================================================================*/

void ni_insert_edges(lb_prob *p, int new_node, neighbor *nbtree, int *intree,
		     int *last, int *lamda, int mu)

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
  int cost = 0, prevcost;
  int pos = 0, ch;
  int i;
  int vertnum = p->vertnum;
  
  for (i=0; i<vertnum; i++){
    if (intree[i] != IN_TREE){
      cost = TCOST(&p->dist, new_node, i, lamda, mu);
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
			 (char *)(nbtree+ch), sizeof(neighbor));
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
    
int new_lamda(lb_prob *p, int upper_bound, int cur_bound, int *lamda,
	      int numroutes, int *tree, edge_data *cur_edges,
	      int alpha)
{
  int gap = upper_bound-cur_bound, multiplier;
  int denom = 0;
  int cur_node1, cur_node2, vertnum = p->vertnum, i;
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
    denom += cur_node1 ? (degrees[cur_node1]-1)*(degrees[cur_node1]-1) : \
      (degrees[cur_node1]-2*numroutes)*(degrees[cur_node1]-2*numroutes);
  
  denom = (int) sqrt((double)denom);

  if (!denom) return(1);

  multiplier = (int) (gap/(denom*alpha));

  for (cur_node1 = 0; cur_node1 < vertnum; cur_node1++)
    lamda[cur_node1] += (degrees[cur_node1] -
				    (cur_node1 ? 1: 2*numroutes));

  if (degrees) free((char *) degrees);
							   
  return(0);
}
