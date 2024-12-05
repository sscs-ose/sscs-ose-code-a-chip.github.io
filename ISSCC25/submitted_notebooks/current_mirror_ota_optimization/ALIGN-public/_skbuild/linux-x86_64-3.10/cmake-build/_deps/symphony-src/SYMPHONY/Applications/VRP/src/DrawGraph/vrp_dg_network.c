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
#include <string.h>

/* SYMPHONY include files */
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_dg.h"

/* VRP include files */
#include "vrp_dg.h"
#include "vrp_const.h"
#include "vrp_macros.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains additional user functions for the draw graph process.
\*===========================================================================*/

/*===========================================================================*\
 * Create the solution graph using adjacency lists
\*===========================================================================*/

dg_net_network *dg_createnet(int vertnum, int length, int *xind, double *xval)
{
   dg_net_edge *nedge;
   dg_net_network *n;
   dg_net_vertex *verts, *nv;
   int v[2], i, j;
   dg_net_elist *adjlist;

   n = (dg_net_network *) calloc(1, sizeof(dg_net_network));
   n->vertnum = vertnum;
   n->edgenum = length;
   n->verts = verts =
      (dg_net_vertex *) calloc(n->vertnum, sizeof(dg_net_vertex));
   n->adjlist = adjlist =
      (dg_net_elist *) malloc(2 * n->edgenum*sizeof(dg_net_elist));
   n->edges = nedge = (dg_net_edge *) calloc(n->edgenum, sizeof(dg_net_edge));

   /*---- set up orignodenum ------------------------------------------------*/
   for (i=vertnum-1; i>=0; i--){
      verts[i].orignodenum = i;
   }

   /*---- set up the adjacency list -----------------------------------------*/
   for (i=0; i<length; i++, xval++, xind++){
      BOTH_ENDS(*xind, &v[1], &v[0]);
      nedge->head = verts + v[0];
      nedge->tail = verts + v[1];
      nedge->weight = *xval;
      for (j=1; j>=0; j--){
	 nv = verts + v[j];
	 if (!nv->first){
	    nv->first = nv->last = adjlist;
	 }else{
	    nv->last->next_edge = adjlist;
	    nv->last = adjlist;
	 }
	 adjlist->next_edge = NULL;
	 nv->degree++;
	 adjlist->data = nedge;
	 adjlist->other = verts + v[1-j];
	 adjlist++;
      }
      nedge++;
   }
   return(n);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free the network
\*===========================================================================*/

void dg_freenet(dg_net_network *n)
{
   if (n){
      FREE(n->adjlist);
      FREE(n->edges);
      FREE(n->verts);
      FREE(n);
   }
}

/*===========================================================================*/

/*===========================================================================*\
 * This function shrinks the chains in the graph
\*===========================================================================*/

void dg_net_shrink_chains(dg_net_network *n)
{
   int vertnum = n->vertnum;
   dg_net_vertex *verts = n->verts;

   dg_net_vertex *nw, *nv1, *nv, *nu;
   dg_net_elist *ne;
   dg_net_edge *dat;

   int i;

   /*------------------------------------------------------------------------*
    * Here we contract all chains of 1-edges, called 1-paths. We simply
    * look at all nodes of degree 2 and keep following the 1-path in each
    * direction from that node until we reach a node that is not of degree 2.
    *------------------------------------------------------------------------*/

   for (i=0; i<vertnum-1; i++){
      nv = verts+i;
      /*-----------check whether we have a degree 2 node-----------*/
      if (nv->scanned != NOT_SCANNED || nv->degree != 2)
	 continue;

      nv->scanned = SCANNED_SHRUNK;

      /*---------------------------------------------------------------------*
       * follow the 1-path from i until we hit a node that is not of degree 2
       * If during this process we come back to nv (i) that means we have a
       * subtour we can contract into one node.
       * Also, as we go along we contract all the nodes on the 1-path into i.
       *---------------------------------------------------------------------*/
      for (ne = nv->first, nw = ne->other; nw->degree == 2; nw = ne->other){
	 ne->data->deleted = TRUE;
	 if (nv == nw)
	    break;
	 nw->scanned = SCANNED_SHRUNK;
	 nv->snode_size++;
	 nw->snode_next = nv->snode_next;
	 nv->snode_next = nw;
	 ne = (nw->first->data->deleted ? nw->last : nw->first);
      }

      if (nv == nw){
	 /* in this case we had a subtour and so we don't need to go on*/
	 nv->first = nv->last = NULL;
	 nv->scanned = SCANNED_ALIVE;
	 continue;
      }

      /* Now nw is not a degree 2 node, but nv->snode_next is the node
       * in the chain adjacent to nw and so on. The number of nodes
       * hanging off nv is exactly nv->snode_size (not including nv) */
      if (nv->snode_size){
	 nv1 = nv->snode_next;
	 if (nv1->first->other != nw){
	    ne = nv1->first;
	    nv1->first = nv1->last;
	    nv1->first->next_edge = ne;
	    nv1->last = ne;
	    ne->next_edge = NULL;
	 }
	 /* Follow the chain back and hang nv to the end */
	 nv1->snode_size = nv->snode_size;
	 for (nu = nv1; nu->snode_next; nu = nu->snode_next);
	 nu->snode_next = nv;
	 nv->snode_next = NULL;
	 nv->snode_size = 0;
      }else{
	 nv1 = nv;
      }

      /* Now nw is next to nv1 and nv1->first->other = nw */

      /* Continue to the other end. */
      for (ne=nv->last, nu=ne->other; nu->degree == 2; nv=nu, nu=ne->other){
	 ne->data->deleted = TRUE;
	 nu->scanned = SCANNED_SHRUNK;
	 nv1->snode_size++;
	 nv->snode_next = nu;
	 ne = (nu->first->data->deleted ? nu->last : nu->first);
      }

      /* Now nv is the last node in the chain, nu the first not degree
       * 2 node, (ne goes from nv to nu) the chain hangs off of nv1 in
       * order, nv1->size is the number of degree 2 nodes in the chain
       * -1 (nv1 itself).
       *
       * Now we update the adjacency lists appropriately. */
      if (nv1->snode_size){
	 nv1->first->next_edge = nv1->last = ne;
	 ne->next_edge = NULL;
	 dat = ne->data;
	 if (dat->head == nu)
	    dat->tail = nv1;
	 else
	    dat->head = nv1;
	 for (ne=nu->first; ne->data != dat; ne=ne->next_edge);
	 ne->other = nv1;
      }
      nv1->scanned = SCANNED_ALIVE;
      /* Now we are completely done. The whole chain is shrinked
       * into nv1, nv1 is connected to appropriately to nw and nu. */
   }

   /* Note that the 'scanned' field is SCANNED_SHRUNK for nodes shrinked into
    * another node; SCANNED_ALIVE for degree 2 nodes still alive and
    * NOT_SCANNED for nodes of degree >= 3 */
}

/*===========================================================================*/

/*===========================================================================*\
 * This function copies a network into a graph which already contains the
 * nodes of the graph. Therefore we have to get rid of the shrunk nodes
 * in the process.
\*===========================================================================*/

void copy_network_into_graph(dg_net_network *n, dg_graph *g)
{
   int i, k, vertnum = n->vertnum, edgenum = n->edgenum;
   dg_net_vertex *verts = n->verts;
   dg_net_edge *ne, *nedges = n->edges;
   dg_node *nod, *gnod, *nodes, *gnodes = g->nodes;
   dg_edge *ge, *gedges = g->edges;

   for (k = i = 0; i < vertnum; i++)
      if (verts[i].scanned != SCANNED_SHRUNK)
	 k++;

   nodes = (dg_node *) malloc(k * sizeof(dg_node));
   for (k = i = 0; i < vertnum; i++){
      if (verts[i].scanned != SCANNED_SHRUNK){
	 nod = nodes + k++;
	 gnod = gnodes + i;
	 *nod = *gnod;
	 if (verts[i].snode_size){ /* if anything is shrunk into this node */
	    sprintf(nod->weight, "%i", verts[i].snode_size);
	 }else{
	    *nod->weight = 0;
	 }
      }
   }
   FREE(gnodes);
   g->nodenum = k;
   g->nodes = nodes;

   for (k = i = 0; i < edgenum; i++)
      if (! nedges[i].deleted)
	 k++;

   gedges = g->edges = (dg_edge *) malloc(k * sizeof(dg_edge));
   for (k = i = 0; i < edgenum; i++){
      if (!(ne=nedges+i)->deleted){
	 ge = gedges + k++;
	 ge->edge_id = INDEX( (ge->tail = ne->tail->orignodenum),
			      (ge->head = ne->head->orignodenum) );
	 ge->deleted = FALSE;
	 if (ne->weight > .99999){
	    strcpy(ge->weight, "1");
	    ge->dash[0] = 0;
	 }else{
	    sprintf(ge->weight, "%.3f", ne->weight);
	    strcpy(ge->dash, "4 3");
	 }
      }
   }
   g->edgenum = k;
}
