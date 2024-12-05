/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <math.h>
#include <memory.h>
#include <stddef.h>
#include <stdlib.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_qsort.h"

/* VRP include files */
#include "network.h"

/*===========================================================================*\
 * Create the solution graph using adjacency lists
\*===========================================================================*/

network *createnet(int *xind, double *xval, int edgenum, double etol,
		   int *edges, int *demand, int vertnum)
{
   register edge *net_edges;
   network *n;
   vertex *verts;
   int nv0, nv1;
   elist *adjlist;
   int i;

   double *val_low, *val_high, val_aux;
   int *ind_low, *ind_high, ind_aux;

   /*------------------------------------------------------------------------*\
    * Allocate the needed memory and set up the data structures
   \*------------------------------------------------------------------------*/
   
   n = (network *) calloc (1, sizeof(network));
   n->vertnum = vertnum;
   n->edgenum = edgenum;/*the number of edges is equal to the number
			  of nonzeros in the LP solution*/
   n->verts = (vertex *) calloc(n->vertnum, sizeof(vertex));
   n->adjlist = (elist *) calloc(2*n->edgenum, sizeof(elist));
   n->edges = (edge *) calloc(n->edgenum, sizeof(edge));
   net_edges = n->edges;
   verts = n->verts;
   adjlist = n->adjlist;
   n->is_integral = TRUE;
   
   qsort_di(xval, xind, edgenum);
   /* qsort_di sorts the array in nondecreasing order;
      now need to translate it into nonincreasing */
   
   for (i = 0, val_low = xval, val_high = xval + edgenum - 1, ind_low = xind,
	   ind_high = xind + edgenum - 1; i < (edgenum/2); i++){
      val_aux = *val_low;
      *val_low++ = *val_high;
      *val_high-- = val_aux;
      ind_aux = *ind_low;
      *ind_low++ = *ind_high;
      *ind_high-- = ind_aux;
   }

   
   /*------------------------------------------------------------------------*\
    * set up the adjacency list
   \*------------------------------------------------------------------------*/
   
   for (i = 0; i < edgenum; i++, xval++, xind++){
      if (*xval < etol) continue;
      if (fabs(floor(*xval+.5) - *xval) > etol){
	 n->is_integral = FALSE;
	 net_edges->weight = *xval;
      }else{
	 net_edges->weight = floor(*xval+.5);
      }
      nv0 = net_edges->v0 = edges[(*xind) << 1];
      nv1 = net_edges->v1 = edges[((*xind)<< 1) + 1];
      if (!verts[nv0].first){
	 verts[nv0].first = verts[nv0].last = adjlist;
	 verts[nv0].degree++;
      }
      else{
	 verts[nv0].last->next_edge = adjlist;
	 verts[nv0].last = adjlist;
	 verts[nv0].degree++;
      }
      adjlist->data = net_edges;
      adjlist->other_end = nv1;
      adjlist->other = verts + nv1;
      adjlist++;
      if (!verts[nv1].first){
	 verts[nv1].first = verts[nv1].last = adjlist;
	 verts[nv1].degree++;
      }
      else{
	 verts[nv1].last->next_edge = adjlist;
	 verts[nv1].last = adjlist;
	 verts[nv1].degree++;
      }
      adjlist->data = net_edges;
      adjlist->other_end = nv0;
      adjlist->other = verts + nv0;
      adjlist++;
      
      net_edges++;
   }
   
   /*set the demand for each node*/
   for (i = 0; i < vertnum; i++){
      verts[i].demand = demand[i];
      verts[i].orignodenum = i;
   }

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
   /*allocate memory for existing nodes list and the binary tree used by
     capforest*/
   n->enodes = (vertex **) calloc (n->vertnum, sizeof(vertex *));
   n->tnodes = (vertex **) calloc (n->vertnum, sizeof(vertex *));
#endif
   
/*___END_EXPERIMENTAL_SECTION___*/
   return(n);
}

/*__BEGIN_EXPERIMENTAL_SECTION__*/
/*===========================================================================*/

network *createnet2(int *xind, double *xval, int edgenum, double etol,
		   int *edges, int *demand, int vertnum, char *status)
{
   register edge *net_edges;
   network *n;
   vertex *verts;
   int nv0, nv1;
   elist *adjlist;
   int i;
   char *stat = status;
   int *sort_order;
   double *tmp;

   double *val_low, *val_high, val_aux;
   int *ind_low, *ind_high, ind_aux;

   /*------------------------------------------------------------------------*\
    * Allocate the needed memory and set up the data structures
   \*------------------------------------------------------------------------*/
   
   n = (network *) calloc (1, sizeof(network));
   n->vertnum = vertnum;
   n->edgenum = edgenum;/*the number of edges is equal to the number
			  of nonzeros in the LP solution*/
   n->verts = (vertex *) calloc(n->vertnum, sizeof(vertex));
   n->adjlist = (elist *) calloc(2*n->edgenum, sizeof(elist));
   n->edges = (edge *) calloc(n->edgenum, sizeof(edge));
   net_edges = n->edges;
   verts = n->verts;
   adjlist = n->adjlist;
   n->is_integral = TRUE;

   tmp = (double *) malloc(edgenum*DSIZE);
   sort_order = (int *) malloc(edgenum*ISIZE);
   for (i = edgenum - 1; i >= 0; i--)
      sort_order[edgenum - i -1] = i;
   memcpy(tmp, xval, edgenum * DSIZE);

   qsort_di(tmp, sort_order, edgenum);
   qsort_ic(sort_order, status, edgenum);
   FREE(tmp);
   FREE(sort_order);
   qsort_di(xval, xind, edgenum);
   /* qsort_di sorts the array in nondecreasing order;
      now need to translate it into nonincreasing */
   
   for (i = 0, val_low = xval, val_high = xval + edgenum - 1, ind_low = xind,
	   ind_high = xind + edgenum - 1; i < (edgenum/2); i++){
      val_aux = *val_low;
      *val_low++ = *val_high;
      *val_high-- = val_aux;
      ind_aux = *ind_low;
      *ind_low++ = *ind_high;
      *ind_high-- = ind_aux;
   }

   
   /*------------------------------------------------------------------------*\
    * set up the adjacency list
   \*------------------------------------------------------------------------*/
   
   for (i = 0; i < edgenum; i++, xval++, xind++, stat++){
      if (*xval < etol) continue;
      if (fabs(floor(*xval+.5) - *xval) > etol){
	 n->is_integral = FALSE;
	 net_edges->weight = *xval;
      }else{
	 net_edges->weight = floor(*xval+.5);
      }
#ifdef COMPILE_OUR_DECOMP
      net_edges->status = *stat;
#endif
      nv0 = net_edges->v0 = edges[(*xind) << 1];
      nv1 = net_edges->v1 = edges[((*xind)<< 1) + 1];
      if (!verts[nv0].first){
	 verts[nv0].first = verts[nv0].last = adjlist;
	 verts[nv0].degree++;
      }
      else{
	 verts[nv0].last->next_edge = adjlist;
	 verts[nv0].last = adjlist;
	 verts[nv0].degree++;
      }
      adjlist->data = net_edges;
      adjlist->other_end = nv1;
      adjlist->other = verts + nv1;
      adjlist++;
      if (!verts[nv1].first){
	 verts[nv1].first = verts[nv1].last = adjlist;
	 verts[nv1].degree++;
      }
      else{
	 verts[nv1].last->next_edge = adjlist;
	 verts[nv1].last = adjlist;
	 verts[nv1].degree++;
      }
      adjlist->data = net_edges;
      adjlist->other_end = nv0;
      adjlist->other = verts + nv0;
      adjlist++;
      
      net_edges++;
   }
   
   /*set the demand for each node*/
   for (i = 0; i < vertnum; i++){
      verts[i].demand = demand[i];
      verts[i].orignodenum = i;
   }

#if 0
   /*allocate memory for existing nodes list and the binary tree used by
     capforest*/
   n->enodes = (vertex **) calloc (n->vertnum, sizeof(vertex *));
   n->tnodes = (vertex **) calloc (n->vertnum, sizeof(vertex *));
#endif
   
   return(n);
}

/*___END_EXPERIMENTAL_SECTION___*/
/*===========================================================================*/

/*===========================================================================*\
 * Calculates the connected components of the solution graph after removing
 * the depot. Each node is assigned the number of the component in which it
 * resides. The number of nodes in each component is put in "compnodes", the
 * total demand of all customers in the component is put in "compdemands", and
 * the value of the cut induced by the component is put in "compcuts".
\*===========================================================================*/

int connected(network *n, int *compnodes, int *compdemands, int *compmembers,
		   double *compcuts, double *compdensity)
{
  int cur_node = 0, cur_comp = 0;
  int cur_member = 0;
  vertex *verts = n->verts;
  int vertnum = n->vertnum;
  elist *cur_edge;
  int *nodes_to_scan, num_nodes_to_scan = 0, i;
  char *is_not_integral = NULL;
  
  nodes_to_scan = (int *) calloc (vertnum, sizeof(int));
  if (compdensity)
     is_not_integral = (char *) calloc (vertnum, sizeof(char));
  
  while (TRUE){
    for (cur_node = 1; cur_node < vertnum; cur_node++)
      if (!verts[cur_node].comp){/*look for a node that hasn't been assigned
				   to a component yet*/
	break;
      }

    if (cur_node == n->vertnum) break;/*this indicates that all nodes have been
					assigned to components*/

    nodes_to_scan[num_nodes_to_scan++] = cur_node;/*add the first node to the
						  list of nodes to be scanned*/
    
    if (compmembers) compmembers[++cur_member] = cur_node;
    
    verts[cur_node].comp = ++cur_comp;/*add the first node into the new
					component*/
    compnodes[cur_comp] = 1;
    verts[cur_node].comp = cur_comp;
    compdemands[cur_comp] = verts[cur_node].demand;
    if (compdensity){
       compdensity[cur_comp] = verts[cur_node].degree;
       if (verts[cur_node].degree != 2)
	  is_not_integral[cur_comp] = TRUE;
    }
    while(TRUE){/*continue to execute this loop until there are no more
		  nodes to scan if there is a node to scan, then add all of
		  its neighbors in to the current component and take it off
		  the list*/
      for (cur_node = nodes_to_scan[--num_nodes_to_scan],
	   verts[cur_node].scanned = TRUE,
	   cur_edge = verts[cur_node].first, cur_comp = verts[cur_node].comp;
	   cur_edge; cur_edge = cur_edge->next_edge){
	if (cur_edge->other_end){
	  if (!verts[cur_edge->other_end].comp){
	    verts[cur_edge->other_end].comp = cur_comp;
	    compnodes[cur_comp]++;
	    if (compmembers) compmembers[++cur_member] = cur_edge->other_end;
	    compdemands[cur_comp] += verts[cur_edge->other_end].demand;
	    if (compdensity){
	       compdensity[cur_comp] += verts[cur_edge->other_end].degree;
	       if (verts[cur_edge->other_end].degree != 2)
		  is_not_integral[cur_comp] = TRUE;
	    }
	    nodes_to_scan[num_nodes_to_scan++] = cur_edge->other_end;
	  }
	}
	else{/*if this node is connected to the depot, then
			     update the value of the cut*/
	  if (compcuts) compcuts[cur_comp] += cur_edge->data->weight;
	  if (compdensity) compdensity[cur_comp] += 1;
	}
      }
      if (!num_nodes_to_scan) break;
    }
  }

  if (compdensity){
     for (i = 1; i <= cur_comp; i++){
	if (is_not_integral[i])
	   compdensity[i] /= 2*(compnodes[i]+1);
	else
	   compdensity[i] = MAXDOUBLE;
     }
  }

  FREE(nodes_to_scan);
  FREE(is_not_integral);

  return(cur_comp);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free the memory associated with the solution graph data structures
\*===========================================================================*/

void free_net(network *n)
{
  int i;
  if (n){
    if (n->adjlist) free ((char *) n->adjlist);
    if (n->verts){
      for (i = 0; i < n->vertnum; i++)
	if (n->verts[i].orig_node_list)
	  free((char *)n->verts[i].orig_node_list);
      free ((char *) n->verts);
    }
    if (n->edges) free((char *) n->edges);
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
    if (n->tnodes) free((char *)n->tnodes);
    if (n->enodes) free((char *)n->enodes);
#endif
/*___END_EXPERIMENTAL_SECTION___*/
    free((char *) n);
  }
}
