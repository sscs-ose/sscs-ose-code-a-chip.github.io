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

#include "mst.h"
#include <string.h>
#include <stdio.h>
void mst(void)
{
  printf("\nIn mst....\n\n");
  lb_prob *p;
  int mytid, info, s_bufid, r_bufid, parent, bytes, msgtag;
  int *tree, *best_tree;
  int *lamda;
  int cur_cost, cur_bound, best_bound = 0, alpha = 0;
  int vertnum, numroutes;
  int y, cur_node1, cur_node2, m1;
  int iter_count = 0, i, k, max_iter;
  int tree_cost, upper_bound;
  edge_data *cheapest_edges, *depot_costs, *best_edges, *cur_edges;
  char best = FALSE;
  double t=0, cpu_time;

  (void) used_time(&t);

  mytid = pvm_mytid();
	
  p = (lb_prob *) calloc ((int)1, sizeof(lb_prob));
  
  /*------------------------------------------------------------------------*\
  |                      Receive the VRP data                                |
  \*------------------------------------------------------------------------*/
  //the block below is same as receive(P), except for freeing r_bufid
  PVM_FUNC(r_bufid, pvm_recv(-1, VRP_BROADCAST_DATA));
  PVM_FUNC(info, pvm_bufinfo(r_bufid, &bytes, &msgtag, &parent));
  PVM_FUNC(info, pvm_upkint(&(p->dist.wtype), 1, 1));
  PVM_FUNC(info, pvm_upkint(&(p->vertnum), 1, 1));
  PVM_FUNC(info, pvm_upkint(&(p->depot), 1, 1));
  PVM_FUNC(info, pvm_upkint(&p->capacity, 1, 1));
  p->demand = (int *) calloc (p->vertnum, sizeof(int));
  PVM_FUNC(info, pvm_upkint(p->demand, p->vertnum, 1));
  p->edgenum = p->vertnum*(p->vertnum-1)/2;
  if (p->dist.wtype){ /* not EXPLICIT */
    p->dist.coordx = (double *) calloc(p->vertnum, sizeof(double));
    p->dist.coordy = (double *) calloc(p->vertnum, sizeof(double));
    PVM_FUNC(info, pvm_upkdouble(p->dist.coordx, (int)p->vertnum, 1));
    PVM_FUNC(info, pvm_upkdouble(p->dist.coordy, (int)p->vertnum, 1));
    if ((p->dist.wtype == _EUC_3D) || (p->dist.wtype == _MAX_3D) || 
        (p->dist.wtype == _MAN_3D)){
      p->dist.coordz = (double *) calloc(p->vertnum, sizeof(double));
      PVM_FUNC(info, pvm_upkdouble(p->dist.coordz, (int)p->vertnum, 1));
    }
  }
  else{ /* EXPLICIT */
    p->dist.cost = (int *) malloc ((int)p->edgenum*sizeof(int));
    PVM_FUNC(info, pvm_upkint(p->dist.cost, (int)p->edgenum, 1));
  }//above mentioned block ends here

  PVM_FUNC(r_bufid, pvm_recv(-1, VRP_LB_DATA));
  PVM_FUNC(info, pvm_upkint(&numroutes, 1, 1));
  PVM_FUNC(info, pvm_upkint(&upper_bound, 1, 1));
  PVM_FUNC(info, pvm_upkint(&max_iter, 1, 1));
  PVM_FUNC(info, pvm_upkint(&m1, 1, 1));

  PVM_FUNC(r_bufid, pvm_recv(-1, VRP_LB_DATA2));
  PVM_FUNC(info, pvm_upkint(&y, 1, 1));
  PVM_FUNC(info, pvm_upkint(&alpha, 1, 1));

  vertnum = p->vertnum;

  /*------------------------------------------------------------------------*\
  |                      Allocate arrays                                     |
  \*------------------------------------------------------------------------*/
  tree           = (int *)      calloc (vertnum, sizeof(int));
  best_tree      = (int *)      calloc (vertnum, sizeof(int));
  lamda          = (int *)          calloc (vertnum, sizeof(int));
  cheapest_edges = (edge_data *)      calloc (vertnum-1, sizeof(edge_data));
  best_edges     = (edge_data *)      calloc (numroutes, sizeof(edge_data));
  cur_edges      = (edge_data *)      calloc (numroutes, sizeof(edge_data));
  depot_costs    = (edge_data *)      calloc (vertnum-1, sizeof(edge_data));

  /*------------------------------------------------------------------------*\
  | My lower bound calculation will follow the methodology in _____________  |
  | See that paper for details.                                              |
  \*------------------------------------------------------------------------*/

  k=2*numroutes-y;
  
  for(iter_count = 0; iter_count < max_iter;){

    /*---------------------------------------------------------------------*\
    | Calculate a k-degree-centre-tree with penalties lamda                 |
    \*---------------------------------------------------------------------*/
    
    tree_cost = make_k_tree(p, tree, lamda, k);

    /*----------------------------------------------------------------------*\
    | Construct a sorted list of the cheapest edges adjacent to each node in |
    | the graph.                                                             |
    \*----------------------------------------------------------------------*/
    
    for (cur_node1 = 1; cur_node1 < vertnum; cur_node1++)
      cheapest_edges[cur_node1-1].cost = MAXINT;
    
    for (cur_node1 = 1; cur_node1 < vertnum; cur_node1++)
      for (cur_node2 = cur_node1 + 1; cur_node2 < vertnum; cur_node2++)
	if (((cur_cost = MCOST(&p->dist, cur_node1, cur_node2, lamda)) <
	     cheapest_edges[cur_node1-1].cost) && tree[cur_node1] != cur_node2
	     && tree[cur_node2] != cur_node1){
	  cheapest_edges[cur_node1-1].cost = cur_cost;
	  cheapest_edges[cur_node1-1].v0 = cur_node1;
	  cheapest_edges[cur_node1-1].v1 = cur_node2;
	}
    
    qsort(cheapest_edges, vertnum-1, sizeof(edge_data), edgecompar);

    /*---------------------------------------------------------------------*\
    | Construct a sorted list of the cheapest edges adjacent to the depot   |
    \*---------------------------------------------------------------------*/
    
    for (cur_node1 = 1; cur_node1 < vertnum; cur_node1++){
      depot_costs[cur_node1-1].cost = MCOST(&p->dist, 0, cur_node1, lamda);
      depot_costs[cur_node1-1].v1 = cur_node1;
    }
    
    qsort(depot_costs, vertnum-1, sizeof(edge_data), edgecompar);

    /*---------------------------------------------------------------------*\
    | Form the bound by taking edges from cheapest_edges and depot_costs,   |
    | along with the tree calculated earlier.                               |
    \*---------------------------------------------------------------------*/
    
    memcpy (cur_edges, cheapest_edges, (numroutes-y)*sizeof(edge_data));
    memcpy (cur_edges+numroutes-y, depot_costs, m1*sizeof(edge_data));
    for (i = 0; i < y-m1; i++)
      cur_edges[numroutes-y+m1+i] = depot_costs[m1+2*i+1];
    for (cur_bound = i = 0; i < numroutes; i++)
      cur_bound += MCOST(&p->dist, cur_edges[i].v0, cur_edges[i].v1, lamda);
    cur_bound += tree_cost;

    /*---------------------------------------------------------------------*\
    | Check if this bound improves the previous best bound                  |
    \*---------------------------------------------------------------------*/
    
    if (cur_bound > best_bound){
      best_bound = cur_bound;
      memcpy (best_tree, tree, vertnum*sizeof(int));
      memcpy (best_edges, cur_edges, numroutes*sizeof(edge_data));
    }

    /*---------------------------------------------------------------------*\
    | Update the penalties and go back to the beginning                     |
    \*---------------------------------------------------------------------*/
    
    iter_count++;
    if ((iter_count == 1) && (!alpha))
      alpha = best_bound/(10*vertnum);
    if (iter_count < max_iter)
      best = new_lamda(p, upper_bound, cur_bound, lamda, numroutes,
		       tree, cur_edges, alpha);

    if ((best) || (iter_count >= max_iter) || (cur_bound < 0)) break;
  }
  
  /*------------------------------------------------------------------------*\
  |        Transmit the tree and best_edges back to the parent               |
  \*------------------------------------------------------------------------*/
  
  PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
  PVM_FUNC(info, pvm_pkint(best_tree, vertnum, 1));
  PVM_FUNC(info, pvm_pkbyte((char *)best_edges, numroutes*sizeof(edge_data),
			     1));
  PVM_FUNC(info, pvm_pkint(&best_bound, 1, 1));
  cpu_time = used_time (&t);
  PVM_FUNC(info, pvm_pkdouble(&cpu_time, 1, 1));
  PVM_FUNC(info, pvm_send(parent, LOWER_BOUND));
  PVM_FUNC(info, pvm_freebuf(s_bufid));
   
  if ( tree )   free ((char *) tree);
  if ( best_tree ) free ((char *) best_tree);
  if ( lamda ) free ((char *) lamda);
  if ( cheapest_edges ) free ((char *) cheapest_edges);
  if ( best_edges ) free ((char *) best_edges);
  if ( cur_edges ) free ((char *) cur_edges);
  if ( depot_costs ) free ((char *) depot_costs);
        
  free_lb_prob(p);
   
}
