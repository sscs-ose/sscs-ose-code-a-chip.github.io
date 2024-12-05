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

/* system include files */
#include <math.h>
#include <memory.h>
#include <stddef.h>
#include <stdlib.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_qsort.h"

/* CNRP include files */
#include "network.h"

/*===========================================================================*\
 * Create the solution graph using adjacency lists
\*===========================================================================*/

network *create_net(int *xind, double *xval, int edgenum, double etol,
		    int *edges, double *demand, int vertnum)
{
   register edge *net_edges;
   network *n;
   vertex *verts;
   int nv0, nv1;
   elist *adjlist;
   int i;
#ifdef DIRECTED_X_VARS
   int total_edgenum = vertnum*(vertnum-1)/2;
   elist *edge1;
   char edge_exists;
#endif
   
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
   
   /*------------------------------------------------------------------------*\
    * set up the adjacency list
   \*------------------------------------------------------------------------*/
   
   for (i = 0; i < edgenum; i++, xval++, xind++){
      if (*xval < etol) continue;
#ifdef DIRECTED_X_VARS
      if (*xind < total_edgenum){
	 nv0 = edges[(*xind) << 1];
	 nv1 = edges[((*xind)<< 1) + 1];
      }else{
	 nv0 = edges[(*xind-total_edgenum) << 1];
	 nv1 = edges[((*xind-total_edgenum)<< 1) + 1];
      }
      for (edge_exists = FALSE, edge1 = verts[nv0].first; edge1;
	   edge1 = edge1->next_edge){
	 if (edge1->other_end == nv1){
	    if (fabs(floor(*xval+.5) - *xval) > etol){
	       edge1->data->weight += *xval;
	    }else{
	       edge1->data->weight += floor(*xval+.5);
	    }
	    edge_exists = TRUE;
	    break;
	 }
      }
      if (edge_exists)
	 continue;
#else
      nv0 = edges[(*xind) << 1];
      nv1 = edges[((*xind)<< 1) + 1];
#endif
      
      if (fabs(floor(*xval+.5) - *xval) > etol){
	 net_edges->weight += *xval;
      }else{
	 net_edges->weight = floor(*xval+.5);
      }
      net_edges->v0 = nv0;
      net_edges->v1 = nv1;
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

   for (i = 0; i < edgenum; i++){
      if (fabs(floor(n->edges[i].weight + .5) - n->edges[i].weight) > etol){
	 n->is_integral = FALSE;
	 break;
      }
   }
   
   /*set the demand for each node*/
   for (i = 0; i < vertnum; i++){
      verts[i].demand = demand[i];
      verts[i].orignodenum = i;
   }

   return(n);
}

/*===========================================================================*\
 * Create the solution graph using adjacency lists
\*===========================================================================*/

network *create_flow_net(int *xind, double *xval, int edgenum, double etol,
			 int *edges, double *demand, int vertnum)
{
   register edge *net_edges;
   network *n;
   vertex *verts;
   int nv0, nv1;
   elist *adjlist;
   int i = 0;
#if defined(DIRECTED_X_VARS) || defined(ADD_FLOW_VARS)
   int total_edgenum = vertnum*(vertnum-1)/2;
   char edge_exists, flow_var;
   elist *edge1;
#endif
#if defined(DIRECTED_X_VARS) && defined(ADD_FLOW_VARS)
   int j;
   char d_x_vars = TRUE;
#elif defined(ADD_FLOW_VARS)
   int j;
   char d_x_vars = FALSE;
#endif
   
   /*------------------------------------------------------------------------*\
    * Allocate the needed memory and set up the data structures
   \*------------------------------------------------------------------------*/
   
   n = (network *) calloc (1, sizeof(network));
   n->vertnum = vertnum;
   n->verts = (vertex *) calloc(vertnum, sizeof(vertex));
   n->adjlist = (elist *) calloc(2*edgenum, sizeof(elist));
   n->edges = (edge *) calloc(edgenum, sizeof(edge));
   net_edges = n->edges;
   verts = n->verts;
   adjlist = n->adjlist;
   n->is_integral = TRUE;
   n->edgenum = 0;
   
   /*------------------------------------------------------------------------*\
    * set up the adjacency list
   \*------------------------------------------------------------------------*/
   
   for (i = 0; i < edgenum; i++){
#if !defined(DIRECTED_X_VARS) && defined(ADD_FLOW_VARS)
      if (xind[i] < total_edgenum){
	 nv0 = edges[xind[i] << 1];
	 nv1 = edges[(xind[i] << 1) + 1];
	 flow_var = FALSE;
      }else if (xind[i] < 2 * total_edgenum){
	 nv0 = edges[(xind[i] - total_edgenum) << 1];
	 nv1 = edges[((xind[i] - total_edgenum) << 1) + 1];
	 flow_var = TRUE;
      }else if (xind[i] < 3 * total_edgenum){
	 nv0 = edges[((xind[i] - 2*total_edgenum) << 1) + 1];
	 nv1 = edges[(xind[i] - 2*total_edgenum) << 1];
	 flow_var = TRUE;
      }else{
	 continue;
      }
      
#elif defined(DIRECTED_X_VARS)
      if (xind[i] < total_edgenum){
	 nv0 = edges[xind[i] << 1];
	 nv1 = edges[(xind[i] << 1) + 1];
	 flow_var = FALSE;
      }else if (xind[i] < 2 * total_edgenum){
	 nv0 = edges[((xind[i] - total_edgenum) << 1) + 1];
	 nv1 = edges[(xind[i] - total_edgenum) << 1];
	 flow_var = FALSE;
      }else if (xind[i] < 3 * total_edgenum){
	 nv0 = edges[(xind[i] - 2 * total_edgenum) << 1];
	 nv1 = edges[((xind[i] - 2 * total_edgenum) << 1) + 1];
	 flow_var = TRUE;	 
      }else if (xind[i] < 4 * total_edgenum){
	 nv0 = edges[((xind[i] - 3 * total_edgenum) << 1) + 1];
	 nv1 = edges[(xind[i] - 3 * total_edgenum) << 1];
	 flow_var = TRUE;
      }else{
	 continue;
      }
#endif

#ifdef ADD_FLOW_VARS
      if (flow_var){
	 for (edge_exists = FALSE, edge1 = verts[nv0].first; edge1;
	      edge1 = edge1->next_edge){
	    if (edge1->other_end == nv1){
	       if (nv0 < nv1){
		  edge1->data->flow1 = xval[i];
	       }else{
		  edge1->data->flow2 = xval[i];
	       }
	       edge_exists = TRUE;
	       break;
	    }
	 }
	 if (edge_exists){
	    continue;
	 }else{
	    if (nv0 < nv1){
	       net_edges->flow1 = xval[i];
	    }else{
	       net_edges->flow2 = xval[i];
	    }
	 }
      }else{
#ifdef DIRECTED_X_VARS
	 for (edge_exists = FALSE, edge1 = verts[nv0].first; edge1;
	      edge1 = edge1->next_edge){
	    if (edge1->other_end == nv1){
	       if (nv0 < nv1){
		  edge1->data->weight += xval[i];
		  edge1->data->weight1 = xval[i];
	       }else{
		  edge1->data->weight += xval[i];
		  edge1->data->weight2 = xval[i];
	       }
	       edge_exists = TRUE;
	       break;
	    }
	 }
	 if (edge_exists){
	    continue;
	 }else{
	    if (nv0 < nv1){
	       net_edges->weight += xval[i];
	       net_edges->weight1 = xval[i];
	    }else{
	       net_edges->weight += xval[i];
	       net_edges->weight2 = xval[i];
	    }
	 }
#else
	 net_edges->weight = xval[i];
#endif
      }
#else
      net_edges->weight = xval[i];
#endif
      
      net_edges->v0 = nv0 < nv1 ? nv0 : nv1;
      net_edges->v1 = nv0 < nv1 ? nv1 : nv0;
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
      n->edgenum++;
   }

   for (i = 0; i < edgenum; i++){
      if (fabs(floor(n->edges[i].weight + .5) - n->edges[i].weight) > etol){
	 n->is_integral = FALSE;
	 break;
      }
   }
   
   /*set the demand for each node*/
   if (demand){
      for (i = 0; i < vertnum; i++){
	 verts[i].demand = demand[i];
	 verts[i].orignodenum = i;
      }
   }

   return(n);
}

/*===========================================================================*/

/*===========================================================================*\
 * Calculates the connected components of the solution graph after removing
 * the depot. Each node is assigned the number of the component in which it
 * resides. The number of nodes in each component is put in "compnodes", the
 * total demand of all customers in the component is put in "compdemands", and
 * the value of the cut induced by the component is put in "compcuts".
\*===========================================================================*/

int connected(network *n, int *compnodes, double *compdemands,
	      int *compmembers, double *compcuts, double *compdensity)
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

int flow_connected(network *n, int *compnodes, double *compdemands,
		   int *compmembers, double *compcuts, double *compdensity,
		   double etol)
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
	 if (cur_edge->data->weight < etol) continue;
	 if (cur_edge->other_end){
	    if (!verts[cur_edge->other_end].comp){
	       verts[cur_edge->other_end].comp = cur_comp;
	       compnodes[cur_comp]++;
	       if (compmembers) compmembers[++cur_member]=cur_edge->other_end;
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
    free((char *) n);
  }
}
